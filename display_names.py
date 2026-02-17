"""Shorten component names for display in terminal and HTML output."""
import re


def shorten_cpu(name: str) -> str:
    """Shorten a CPU name to its model identifier.

    "AMD Ryzen 7 9850X3D - Ryzen 7 9000 Series 8-Core 5.6GHz ..." → "AMD Ryzen 7 9850X3D"
    "Intel Core i7-14700K - 14th Gen Raptor Lake ..." → "Intel Core i7-14700K"
    """
    if not name:
        return name
    # Cut at first " - " delimiter (Newegg full titles)
    short = name.split(" - ")[0].strip()
    # Also strip trailing SKU codes like "100-100001973WOF"
    short = re.sub(r"\s+\d{3}-\d{9,}\w*$", "", short)
    return short


def shorten_ram(name: str) -> str:
    """Shorten a RAM name to brand + capacity + DDR speed.

    "CORSAIR Vengeance RGB 32GB (2 x 16GB) 288-Pin PC RAM DDR5 6400
     (PC5 51200) Desktop Memory Model CMH32GX5M2N6400C36"
    → "CORSAIR Vengeance RGB 32GB (2x16GB) DDR5 6400"
    """
    if not name:
        return name
    # Strip everything from "Desktop Memory" or "Desktop Upgrade" onward
    short = re.split(r"\s+Desktop\s+(?:Memory|Upgrade)\b", name, flags=re.IGNORECASE)[0]
    # Strip "Gaming Desktop" suffix too
    short = re.split(r"\s+Gaming\s+Desktop\b", short, flags=re.IGNORECASE)[0]
    # Strip "288-Pin PC RAM" or "288-Pin PC"
    short = re.sub(r"\s*288-Pin\s+PC\s*(?:RAM)?\s*", " ", short)
    # Strip "(PC5 NNNNN)" bandwidth notation
    short = re.sub(r"\s*\(PC\d\s+\d+\)", "", short)
    # Strip trailing model/SKU codes (all-caps+digits, 10+ chars)
    short = re.sub(r"\s+(?:Model\s+)?[A-Z0-9]{10,}\w*$", "", short)
    # Trim after speed: keep up to "DDR5 NNNN" or "NNNNMHz" but drop CL/voltage/IC info
    short = re.sub(r"(\d{4,5}\s*MHz)\s+CL\d.*$", r"\1", short, flags=re.IGNORECASE)
    # Strip trailing ", for AMD EXPO" / ", for Intel XMP"
    short = re.sub(r",?\s+for\s+(?:AMD|Intel)\b.*$", "", short, flags=re.IGNORECASE)
    # Strip "Series" if at end
    short = re.sub(r"\s+Series\s*$", "", short)
    # Normalize whitespace
    short = " ".join(short.split())
    return short.strip()


def shorten_motherboard(name: str) -> str:
    """Shorten a motherboard name to brand + model + socket.

    "ASUS TUF GAMING X870E-PLUS WIFI7 AMD X870E ATX Motherboard with
     16+2+1 80A Power Stages, DDR5 Support ..."
    → "ASUS TUF GAMING X870E-PLUS WIFI7"

    "GIGABYTE B850 GAMING X WIFI6E AMD AM5 LGA 1718 Motherboard, ATX,
     DDR5, 3x M.2, ..."
    → "GIGABYTE B850 GAMING X WIFI6E"
    """
    if not name:
        return name
    # Cut at first comma (feature lists)
    short = name.split(",")[0].strip()
    # Strip "with ..." suffix (ASUS pattern: "Motherboard with 16+2+1...")
    short = re.split(r"\s+with\s+\d", short)[0].strip()
    # Strip trailing generic words: "Motherboard"/"mainboard" with optional ATX prefix
    short = re.sub(
        r"\s+(?:(?:Micro[- ]?|Extended\s+|E-)?ATX\s+)?(?:[Mm]otherboard|[Mm]ainboard)\s*$",
        "", short,
    )
    # Iteratively strip trailing platform/socket/form-factor/retailer noise
    for _ in range(4):
        short = re.sub(
            r"\s+(?:AMD\s+)?(?:AM\d|LGA\s*\d{4})\s*$", "", short, flags=re.IGNORECASE,
        )
        short = re.sub(
            r"\s+AMD\s+(?:X\d{3}\w?|B\d{3}\w?)\s*$", "", short, flags=re.IGNORECASE,
        )
        short = re.sub(
            r"\s+(?:E-|Extended\s*|Micro[- ]?)?ATX\s*$", "", short, flags=re.IGNORECASE,
        )
        # Strip "Ultra Core (Series N)" retailer branding (Newegg Z890 pattern)
        short = re.sub(r"\s+Ultra\s+Core\s*(?:\(Series\s*\d\))?\s*$", "", short, flags=re.IGNORECASE)
        # Strip trailing "(Series N)" standalone
        short = re.sub(r"\s*\(Series\s*\d\)\s*$", "", short, flags=re.IGNORECASE)
        # Strip "AMD RYZEN NNNN" processor family suffix (Newegg B650 pattern)
        short = re.sub(r"\s+AMD\s+RYZEN\s+\d{4}\s*$", "", short, flags=re.IGNORECASE)
    return short.strip()
