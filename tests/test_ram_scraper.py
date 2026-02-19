# tests/test_ram_scraper.py
from scrapers.ram import _is_likely_ram, _parse_ram_deal, _parse_price


class TestIsLikelyRam:
    def test_ddr5_memory_kit(self):
        assert _is_likely_ram("G.SKILL Trident Z5 64GB DDR5-6000 Desktop Memory") is True

    def test_corsair_vengeance(self):
        assert _is_likely_ram("CORSAIR Vengeance RGB 48GB (2x24GB) DDR5-6400") is True

    def test_laptop_ram_sodimm(self):
        assert _is_likely_ram("Crucial 64GB DDR5-5600 SODIMM Laptop Memory") is False

    def test_monitor(self):
        assert _is_likely_ram("Samsung 32GB UHD Monitor") is False

    def test_ssd(self):
        assert _is_likely_ram("Samsung 980 Pro NVMe SSD 2TB") is False

    def test_motherboard(self):
        assert _is_likely_ram("ASUS ROG STRIX X870E-E Motherboard") is False

    def test_cpu(self):
        assert _is_likely_ram("AMD Ryzen 7 9800X3D Processor") is False

    def test_brand_name_only(self):
        assert _is_likely_ram("Corsair Vengeance 64GB Kit") is True

    def test_gpu(self):
        assert _is_likely_ram("NVIDIA RTX 4090 24GB Graphics Card") is False

    def test_kingston_fury(self):
        assert _is_likely_ram("Kingston FURY Beast 96GB (2x48GB) DDR5-6000") is True

    def test_ripjaws(self):
        assert _is_likely_ram("G.SKILL Ripjaws S5 128GB (4x32GB) DDR5-6000") is True


class TestParseRamDeal:
    def test_basic_ram_listing(self):
        deal = _parse_ram_deal(
            "G.SKILL Trident Z5 64GB (2x32GB) DDR5-6000",
            189.99, "https://www.newegg.com/p/N82E123", "Newegg",
        )
        assert deal is not None
        assert deal.capacity_gb == 64
        assert deal.speed_mhz == 6000
        assert deal.ddr_version == 5
        assert deal.price == 189.99

    def test_kit_format_2x24(self):
        deal = _parse_ram_deal(
            "CORSAIR Vengeance 48GB (2x24GB) DDR5-6400",
            159.99, "https://example.com", "Amazon",
        )
        assert deal is not None
        assert deal.capacity_gb == 48

    def test_rejects_ddr4(self):
        deal = _parse_ram_deal(
            "G.SKILL Ripjaws V 64GB DDR4-3600",
            149.99, "https://example.com", "Newegg",
        )
        assert deal is None

    def test_rejects_non_ram(self):
        deal = _parse_ram_deal(
            "ASUS 27-inch Gaming Monitor",
            299.99, "https://example.com", "Amazon",
        )
        assert deal is None

    def test_rejects_zero_price(self):
        deal = _parse_ram_deal(
            "G.SKILL 64GB DDR5-6000",
            0.0, "https://example.com", "Newegg",
        )
        assert deal is None

    def test_rejects_laptop_ram(self):
        deal = _parse_ram_deal(
            "Crucial 64GB DDR5-5600 SODIMM Laptop Memory",
            159.99, "https://example.com", "Amazon",
        )
        assert deal is None

    def test_96gb_kit(self):
        deal = _parse_ram_deal(
            "Kingston FURY Beast 96GB (2x48GB) DDR5-6000 Desktop Memory",
            349.99, "https://example.com", "MicroCenter",
        )
        assert deal is not None
        assert deal.capacity_gb == 96

    def test_128gb_kit(self):
        deal = _parse_ram_deal(
            "G.SKILL Trident Z5 128GB (4x32GB) DDR5-6000",
            599.99, "https://example.com", "BHPhoto",
        )
        assert deal is not None
        assert deal.capacity_gb == 128


class TestParsePrice:
    def test_basic(self):
        assert _parse_price("$189.99") == 189.99

    def test_comma(self):
        assert _parse_price("$1,299.99") == 1299.99

    def test_empty(self):
        assert _parse_price("") == 0.0

    def test_no_dollar(self):
        assert _parse_price("189.99") == 189.99
