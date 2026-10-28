import ipaddress
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import subredes  # noqa: E402


class TestConversiones(unittest.TestCase):
    def test_ida_y_vuelta(self):
        for ip in ["0.0.0.0", "192.168.1.10", "255.255.255.255", "10.0.0.1"]:
            self.assertEqual(subredes.int_a_ip(subredes.ip_a_int(ip)), ip)

    def test_ip_invalida(self):
        for mala in ["256.1.1.1", "1.2.3", "a.b.c.d", "1.2.3.4.5", ""]:
            with self.assertRaises(ValueError):
                subredes.ip_a_int(mala)

    def test_mascaras(self):
        self.assertEqual(subredes.int_a_ip(subredes.mascara_desde_prefijo(24)), "255.255.255.0")
        self.assertEqual(subredes.int_a_ip(subredes.mascara_desde_prefijo(26)), "255.255.255.192")
        self.assertEqual(subredes.int_a_ip(subredes.mascara_desde_prefijo(0)), "0.0.0.0")
        self.assertEqual(subredes.prefijo_desde_mascara("255.255.254.0"), 23)

    def test_mascara_no_contigua(self):
        with self.assertRaises(ValueError):
            subredes.prefijo_desde_mascara("255.0.255.0")

    def test_prefijo_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            subredes.mascara_desde_prefijo(33)


class TestInfoRed(unittest.TestCase):
    def test_ejemplo_conocido(self):
        ip, p = subredes.parsear_red("192.168.1.130/26")
        d = subredes.info_red(ip, p)
        self.assertEqual(d["red"], "192.168.1.128")
        self.assertEqual(d["broadcast"], "192.168.1.191")
        self.assertEqual(d["primer_host"], "192.168.1.129")
        self.assertEqual(d["ultimo_host"], "192.168.1.190")
        self.assertEqual(d["hosts_utiles"], 62)

    def test_con_mascara_decimal(self):
        ip, p = subredes.parsear_red("10.0.5.9", "255.255.254.0")
        d = subredes.info_red(ip, p)
        self.assertEqual(d["red"], "10.0.4.0")
        self.assertEqual(d["broadcast"], "10.0.5.255")

    def test_casos_borde(self):
        d31 = subredes.info_red(subredes.ip_a_int("10.0.0.1"), 31)
        self.assertEqual(d31["hosts_utiles"], 2)
        d32 = subredes.info_red(subredes.ip_a_int("10.0.0.1"), 32)
        self.assertEqual(d32["hosts_utiles"], 1)
        self.assertEqual(d32["primer_host"], "10.0.0.1")

    def test_contra_modulo_ipaddress(self):
        """Compara 500 casos aleatorios (semilla fija) con la biblioteca estándar."""
        azar = random.Random(2026)
        for _ in range(500):
            ip_int = azar.getrandbits(32)
            prefijo = azar.randint(0, 32)
            d = subredes.info_red(ip_int, prefijo)
            ref = ipaddress.ip_network((ip_int, prefijo), strict=False)
            self.assertEqual(d["red"], str(ref.network_address))
            self.assertEqual(d["broadcast"], str(ref.broadcast_address))
            self.assertEqual(d["mascara"], str(ref.netmask))
            self.assertEqual(d["wildcard"], str(ref.hostmask))
            if prefijo <= 30:
                self.assertEqual(d["hosts_utiles"], ref.num_addresses - 2)
            else:
                self.assertEqual(d["hosts_utiles"], ref.num_addresses)


class TestDividir(unittest.TestCase):
    def test_cuatro_subredes(self):
        s = subredes.dividir("192.168.10.0/24", 4)
        self.assertEqual([x["red"] for x in s],
                         ["192.168.10.0", "192.168.10.64", "192.168.10.128", "192.168.10.192"])
        self.assertTrue(all(x["prefijo"] == 26 for x in s))

    def test_redondea_hacia_arriba(self):
        self.assertEqual(len(subredes.dividir("10.0.0.0/16", 5)), 8)

    def test_coincide_con_ipaddress(self):
        esperado = [str(n) for n in ipaddress.ip_network("172.16.0.0/16").subnets(prefixlen_diff=3)]
        obtenido = [f"{x['red']}/{x['prefijo']}" for x in subredes.dividir("172.16.0.0/16", 8)]
        self.assertEqual(obtenido, esperado)

    def test_no_se_puede_dividir_mas_alla_de_32(self):
        with self.assertRaises(ValueError):
            subredes.dividir("10.0.0.0/30", 16)


class TestVlsm(unittest.TestCase):
    def test_ejemplo_clasico(self):
        r = subredes.vlsm("192.168.0.0/24", [100, 50, 20, 2])
        self.assertEqual([(x["red"], x["prefijo"]) for x in r],
                         [("192.168.0.0", 25), ("192.168.0.128", 26),
                          ("192.168.0.192", 27), ("192.168.0.224", 30)])

    def test_ordena_de_mayor_a_menor(self):
        r = subredes.vlsm("10.0.0.0/24", [2, 100])
        self.assertEqual(r[0]["hosts_pedidos"], 100)

    def test_sin_espacio(self):
        with self.assertRaises(ValueError):
            subredes.vlsm("192.168.0.0/24", [200, 100])

    def test_todas_alcanzan_los_hosts_pedidos(self):
        for x in subredes.vlsm("10.0.0.0/16", [1000, 300, 60, 10, 2]):
            self.assertGreaterEqual(x["hosts_utiles"], x["hosts_pedidos"])

    def test_hosts_invalidos(self):
        with self.assertRaises(ValueError):
            subredes.vlsm("10.0.0.0/24", [0])


if __name__ == "__main__":
    unittest.main()
