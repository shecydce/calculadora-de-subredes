"""Calculadora de subredes IPv4 (sin librerías externas).

Los cálculos se hacen con operaciones de bits sobre enteros de 32 bits, a propósito,
para entender cómo funciona el direccionamiento. Los tests comparan los resultados con
el módulo `ipaddress` de la biblioteca estándar.

Uso:
    python subredes.py info 192.168.1.130/26
    python subredes.py info 10.0.5.9 255.255.254.0
    python subredes.py dividir 192.168.10.0/24 4
    python subredes.py vlsm 192.168.0.0/24 100 50 20 2
"""
import argparse
import math

TOTAL_BITS = 32
MAX_VALOR = 0xFFFFFFFF


def ip_a_int(ip):
    """Convierte '192.168.1.10' en un entero de 32 bits. Valida el formato."""
    partes = ip.strip().split(".")
    if len(partes) != 4:
        raise ValueError(f"IP inválida: {ip!r} (se esperan 4 octetos)")
    valor = 0
    for p in partes:
        if not p.isdigit() or not 0 <= int(p) <= 255:
            raise ValueError(f"IP inválida: {ip!r} (octeto fuera de 0-255)")
        valor = (valor << 8) | int(p)
    return valor


def int_a_ip(valor):
    """Convierte un entero de 32 bits en 'a.b.c.d'."""
    return ".".join(str((valor >> desplazamiento) & 255) for desplazamiento in (24, 16, 8, 0))


def mascara_desde_prefijo(prefijo):
    """Entero de la máscara para un prefijo /0 a /32."""
    if not 0 <= prefijo <= TOTAL_BITS:
        raise ValueError(f"Prefijo inválido: {prefijo} (debe estar entre 0 y 32)")
    if prefijo == 0:
        return 0
    return (MAX_VALOR << (TOTAL_BITS - prefijo)) & MAX_VALOR


def prefijo_desde_mascara(mascara):
    """Prefijo a partir de una máscara '255.255.255.0'. Valida que los unos sean contiguos."""
    valor = ip_a_int(mascara)
    prefijo = bin(valor).count("1")
    if mascara_desde_prefijo(prefijo) != valor:
        raise ValueError(f"Máscara inválida: {mascara!r} (los bits en 1 deben ser contiguos)")
    return prefijo


def parsear_red(texto, mascara=None):
    """Acepta '192.168.1.10/24' o una IP con máscara aparte. Devuelve (ip_int, prefijo)."""
    if mascara is not None:
        return ip_a_int(texto), prefijo_desde_mascara(mascara)
    if "/" not in texto:
        raise ValueError("Indicá el prefijo (por ejemplo 192.168.1.10/24) o una máscara")
    ip, prefijo = texto.split("/", 1)
    if not prefijo.isdigit():
        raise ValueError(f"Prefijo inválido: {prefijo!r}")
    prefijo = int(prefijo)
    mascara_desde_prefijo(prefijo)  # valida el rango
    return ip_a_int(ip), prefijo


def info_red(ip_int, prefijo):
    """Calcula los datos de la red a la que pertenece una IP."""
    mascara = mascara_desde_prefijo(prefijo)
    red = ip_int & mascara
    broadcast = red | (~mascara & MAX_VALOR)
    cantidad = 2 ** (TOTAL_BITS - prefijo)

    if prefijo == 32:
        primer, ultimo, hosts = red, red, 1
    elif prefijo == 31:  # enlace punto a punto (RFC 3021): sin red ni broadcast reservados
        primer, ultimo, hosts = red, broadcast, 2
    else:
        primer, ultimo, hosts = red + 1, broadcast - 1, cantidad - 2

    return {
        "red": int_a_ip(red),
        "prefijo": prefijo,
        "mascara": int_a_ip(mascara),
        "wildcard": int_a_ip(~mascara & MAX_VALOR),
        "broadcast": int_a_ip(broadcast),
        "primer_host": int_a_ip(primer),
        "ultimo_host": int_a_ip(ultimo),
        "hosts_utiles": hosts,
        "direcciones_totales": cantidad,
    }


def dividir(red_texto, cantidad_subredes):
    """Divide una red en subredes del mismo tamaño.

    Si la cantidad pedida no es potencia de 2 se redondea hacia arriba
    (por ejemplo 5 -> 8 subredes), porque cada bit prestado duplica la cantidad.
    """
    if cantidad_subredes < 1:
        raise ValueError("La cantidad de subredes debe ser al menos 1")
    ip_int, prefijo = parsear_red(red_texto)
    base = ip_int & mascara_desde_prefijo(prefijo)
    bits_prestados = math.ceil(math.log2(cantidad_subredes))
    nuevo_prefijo = prefijo + bits_prestados
    if nuevo_prefijo > TOTAL_BITS:
        raise ValueError(f"No se puede dividir /{prefijo} en {cantidad_subredes} subredes")
    tamano = 2 ** (TOTAL_BITS - nuevo_prefijo)
    return [info_red(base + i * tamano, nuevo_prefijo) for i in range(2 ** bits_prestados)]


def vlsm(red_texto, hosts_necesarios):
    """Asigna subredes de tamaño variable (VLSM) según los hosts que necesita cada una.

    Se ordenan de mayor a menor para que cada bloque quede alineado dentro de la red base.
    """
    ip_int, prefijo = parsear_red(red_texto)
    base = ip_int & mascara_desde_prefijo(prefijo)
    limite = base + 2 ** (TOTAL_BITS - prefijo)
    siguiente = base
    resultado = []
    for hosts in sorted(hosts_necesarios, reverse=True):
        if hosts < 1:
            raise ValueError("Cada subred debe necesitar al menos 1 host")
        bits_host = max(2, math.ceil(math.log2(hosts + 2)))  # +2: red y broadcast
        nuevo_prefijo = TOTAL_BITS - bits_host
        tamano = 2 ** bits_host
        if siguiente + tamano > limite:
            raise ValueError("La red base no tiene espacio suficiente para todas las subredes")
        datos = info_red(siguiente, nuevo_prefijo)
        datos["hosts_pedidos"] = hosts
        resultado.append(datos)
        siguiente += tamano
    return resultado


def _mostrar(datos):
    return (
        f"Red:        {datos['red']}/{datos['prefijo']}\n"
        f"Máscara:    {datos['mascara']}  (wildcard {datos['wildcard']})\n"
        f"Broadcast:  {datos['broadcast']}\n"
        f"Hosts:      {datos['primer_host']} - {datos['ultimo_host']}  ({datos['hosts_utiles']} útiles)"
    )


def main():
    parser = argparse.ArgumentParser(description="Calculadora de subredes IPv4")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_info = sub.add_parser("info", help="datos de la red de una IP")
    p_info.add_argument("ip", help="IP con prefijo (192.168.1.10/24) o sola, si se pasa la máscara")
    p_info.add_argument("mascara", nargs="?", help="máscara en formato decimal, opcional")

    p_div = sub.add_parser("dividir", help="dividir una red en N subredes iguales")
    p_div.add_argument("red", help="red en formato CIDR, por ejemplo 192.168.10.0/24")
    p_div.add_argument("cantidad", type=int)

    p_vlsm = sub.add_parser("vlsm", help="asignar subredes según hosts necesarios")
    p_vlsm.add_argument("red", help="red base en formato CIDR")
    p_vlsm.add_argument("hosts", type=int, nargs="+", help="hosts que necesita cada subred")

    args = parser.parse_args()
    try:
        if args.comando == "info":
            ip_int, prefijo = parsear_red(args.ip, args.mascara)
            print(_mostrar(info_red(ip_int, prefijo)))
        elif args.comando == "dividir":
            for i, s in enumerate(dividir(args.red, args.cantidad), start=1):
                print(f"--- Subred {i} ---\n{_mostrar(s)}")
        else:
            for s in vlsm(args.red, args.hosts):
                print(f"--- Necesita {s['hosts_pedidos']} hosts ---\n{_mostrar(s)}")
    except ValueError as e:
        parser.exit(2, f"Error: {e}\n")


if __name__ == "__main__":
    main()
