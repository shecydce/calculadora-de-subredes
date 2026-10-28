# Calculadora de subredes IPv4

Herramienta de línea de comandos en Python para calcular direccionamiento IPv4: datos de una red, división en subredes iguales y asignación VLSM. Los cálculos se hacen **con operaciones de bits sobre enteros de 32 bits** (sin usar el módulo `ipaddress` en el código), para entender cómo funciona por dentro. Los tests comparan los resultados con `ipaddress` como referencia.

Sin dependencias externas: solo Python 3.

## Comandos

### `info`: datos de la red de una IP
```bash
python subredes.py info 192.168.1.130/26
python subredes.py info 10.0.5.9 255.255.254.0
```
```
Red:        192.168.1.128/26
Máscara:    255.255.255.192  (wildcard 0.0.0.63)
Broadcast:  192.168.1.191
Hosts:      192.168.1.129 - 192.168.1.190  (62 útiles)
```

### `dividir`: N subredes del mismo tamaño
```bash
python subredes.py dividir 192.168.10.0/24 4
```
Primeras subredes de la salida:
```
--- Subred 1 ---
Red:        192.168.10.0/26
Máscara:    255.255.255.192  (wildcard 0.0.0.63)
Broadcast:  192.168.10.63
Hosts:      192.168.10.1 - 192.168.10.62  (62 útiles)
--- Subred 2 ---
Red:        192.168.10.64/26
Máscara:    255.255.255.192  (wildcard 0.0.0.63)
Broadcast:  192.168.10.127
Hosts:      192.168.10.65 - 192.168.10.126  (62 útiles)
...
```
Si la cantidad no es potencia de 2 se redondea hacia arriba (5 pasa a 8), porque cada bit prestado duplica la cantidad de subredes.

### `vlsm`: subredes de tamaño variable según los hosts necesarios
```bash
python subredes.py vlsm 192.168.0.0/24 100 50 20 2
```
```
--- Necesita 100 hosts ---
Red:        192.168.0.0/25
Máscara:    255.255.255.128  (wildcard 0.0.0.127)
Broadcast:  192.168.0.127
Hosts:      192.168.0.1 - 192.168.0.126  (126 útiles)
--- Necesita 50 hosts ---
Red:        192.168.0.128/26
Máscara:    255.255.255.192  (wildcard 0.0.0.63)
Broadcast:  192.168.0.191
Hosts:      192.168.0.129 - 192.168.0.190  (62 útiles)
--- Necesita 20 hosts ---
Red:        192.168.0.192/27
Máscara:    255.255.255.224  (wildcard 0.0.0.31)
Broadcast:  192.168.0.223
Hosts:      192.168.0.193 - 192.168.0.222  (30 útiles)
--- Necesita 2 hosts ---
Red:        192.168.0.224/30
Máscara:    255.255.255.252  (wildcard 0.0.0.3)
Broadcast:  192.168.0.227
Hosts:      192.168.0.225 - 192.168.0.226  (2 útiles)
```

## Cómo funciona
- Una IP es un entero de 32 bits: `192.168.1.10` se arma desplazando cada octeto 24, 16, 8 y 0 bits.
- La **máscara** de prefijo `/n` son `n` unos seguidos de ceros.
- **Red** = IP AND máscara. **Broadcast** = red OR (NOT máscara).
- Hosts útiles = 2^(32-n) - 2, con dos casos especiales: `/31` (enlace punto a punto, 2 hosts) y `/32` (1 host).
- VLSM: se ordenan los pedidos de mayor a menor y a cada uno se le da el bloque más chico que alcance (hosts + 2 por red y broadcast), así los bloques quedan alineados.

## Tests
```bash
python -m unittest discover -s tests -v
```
Incluyen 500 casos aleatorios (con semilla fija) comparados contra `ipaddress`, casos borde (`/0`, `/31`, `/32`), máscaras inválidas y errores de espacio en VLSM.

## Ejercicios para profundizar
- Agregar un comando `pertenece IP RED` que diga si una IP está dentro de una red.
- Mostrar también la representación binaria de la IP y la máscara.
- Agregar soporte para IPv6 básico.
- Resolver a mano el ejemplo de VLSM y verificar que coincide con la salida.
