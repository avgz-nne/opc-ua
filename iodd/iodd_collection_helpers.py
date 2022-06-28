import json
import os
import xml.etree.ElementTree as ET

from iodd.iodd import IODD


def load_collection(collection_folder: str = "collection") -> list[IODD]:
    with open(
        os.path.join(os.getcwd(), "iodd", collection_folder, "iodd_collection_index.json"), "r"
    ) as f:
        iodd_collection = json.loads(f.read())
    iodds = []
    for entry in iodd_collection:
        iodds.append(IODD(entry["file"]))
    return iodds


def update_iodd_collection(iodd_collection_loc: str = "collection") -> None:
    """Update the IODD collection file.

    :param iodd_collection_loc: _description_, defaults to "iodd"
    """
    iodd_schema_loc = "{http://www.io-link.com/IODD/2010/10}"

    iodd_collection = [
        (os.path.join(os.getcwd(), "iodd", iodd_collection_loc, file), file)
        for file in os.listdir(path=os.path.join(os.getcwd(), "iodd", iodd_collection_loc))
    ]

    updated_iodd_collection: list[dict] = []
    for file in iodd_collection:
        if file[1] in [
            "iodd_collection_index.json",

        ]:
            continue
        tree = ET.parse(source=file[0])
        root = tree.getroot()
        device_variants = root.findall(
            f"./{iodd_schema_loc}ProfileBody"
            f"/{iodd_schema_loc}DeviceIdentity"
            f"/{iodd_schema_loc}DeviceVariantCollection"
            f"/{iodd_schema_loc}DeviceVariant"
        )
        variants = [dv.get("productId") for dv in device_variants]
        updated_iodd_collection.append(
            {"family": variants, "file": os.path.join(os.getcwd(), "iodd", "collection", file[1])}
        )
    with open(
        os.path.join(os.getcwd(), "iodd", iodd_collection_loc, "iodd_collection_index.json"), "w"
    ) as f:
        json.dump(updated_iodd_collection, f, indent=4)
