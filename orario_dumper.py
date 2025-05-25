import fitz  # PyMuPDF
import json
import re
import sys
from os.path import exists
from typing import Dict, List, Optional, Tuple, Union

# Constants
WEEKDAYS = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato"]

# File type identifiers
TYPE_A = 'A'  # Chiusi -> Settimana A
TYPE_B = 'B'  # Standard settimana B per tutti


def create_template_json(include_saturday: bool = True) -> Dict:
    """Create an empty template for schedule data."""
    template = {}
    days = WEEKDAYS if include_saturday else WEEKDAYS[:-1]

    for day in days:
        template[day] = {
            "materie": [],
            "professori": [],
            "aule": []
        }

    return template


def clean_text(text: str) -> List[str]:
    """Clean text from unicode characters and empty lines."""
    text = re.sub(r'(\s+\uea1e)|(\uea1e)', "", text).strip().splitlines()

    # Remove specific single characters
    return [line for line in text if line not in ["a", "s"]]


def is_aula(text: str) -> bool:
    """Check if the text represents a classroom."""
    return ("(" in text or "PALESTRA" in text or
            text == "Tesauro LAB.INFORMATICA" or "HOME" in text or "Tesauro204")


def add_to_json(block: List[str], day: str, template: Dict, single_hour: int = 0) -> None:
    """Add block data to the JSON template."""
    # For two-hour blocks, duplicate entries
    if len(block) < 6 and single_hour == 0:
        block.extend(block[:len(block)])

    k = 0

    for i in range(2 - single_hour):
        template[day]["materie"].append(block[0 + k])
        template[day]["professori"].append(block[1 + k])

        # Check for co-teacher
        if not is_aula(block[2 + k]):
            template[day]["professori"][-1] = f"{template[day]['professori'][-1]},{block[2 + k]}"
            k += 1

        template[day]["aule"].append(block[k + 2])

        # Check for additional classroom
        if len(block) / 2 == 5:
            template[day]["aule"][-1] = f"{template[day]['aule'][-1]},{block[3 + k]}"
            k += 1

        # Move to next entry
        k += 3

def extract_text_block(page, rect: Tuple[float, float, float, float]) -> List[str]:
    """Extract and clean text from a specific rectangle on a page."""
    block = page.get_textbox(fitz.Rect(*rect))
    return clean_text(block)


def process_schedule_block(page, day_index: int, x_offset: float, y_start: float,
                           template: Dict, day_name: str) -> None:
    """Process a complete schedule block for one day."""
    ora_singola1 = ora_singola2 = ora_singola3 = 0
    offset_y = offset_x = 0
    blocco4 = None

    # First block (hours 1-2)
    base_x = x_offset + (125 * day_index)
    blocco1 = extract_text_block(page, (base_x, y_start, base_x + 120, y_start + 140))

    if not blocco1:
        return


    # Check if first hour is single
    if blocco1 and not is_aula(blocco1[-1]):
        blocco1 = extract_text_block(page, (base_x, y_start, base_x + 120, y_start + 60))
        ora_singola1 = 1
        offset_y = 80
        offset_x = 60

    add_to_json(blocco1, day_name, template, ora_singola1)

    # Second block (hours 3-4)
    blocco2 = extract_text_block(page,
                                 (base_x, y_start + 150 - offset_x,
                                  base_x + 120, y_start + 290 - offset_y))
    if len(blocco2) == 0:
        blocco2 = extract_text_block(page, (base_x, y_start + 150 - offset_x, base_x + 120, y_start + 450 - offset_y))
        add_to_json(blocco2, day_name, template, ora_singola2)
    else:
        # Check if second block is single hour
        if blocco2 and not is_aula(blocco2[-1]):
            blocco2 = extract_text_block(page, (base_x, y_start + 150, base_x + 120, y_start + 220))
            ora_singola2 = 1
            offset_y = 80
            offset_x = 60

        add_to_json(blocco2, day_name, template, ora_singola2)
        # Third block (hours 5-6)
        blocco3 = extract_text_block(page,
                                     (base_x, y_start + 310 - offset_x,
                                      base_x + 120, y_start + 460 - offset_y))

        # Check if third block needs special handling
        if blocco3 and not is_aula(blocco3[-1]):
            if ora_singola2 == 0:
                ora_singola3 = 1
                offset_x = 80
                blocco3 = extract_text_block(page, (base_x, y_start + 230, base_x + 120, y_start + 290))

            # Fourth block (if applicable)
            blocco4 = extract_text_block(page,
                                         (base_x, y_start + 390 - offset_x,
                                          base_x + 120, y_start + 460))

        add_to_json(blocco3, day_name, template, ora_singola3)
        if blocco4 is not None:
            add_to_json(blocco4, day_name, template)
def process_type_a(doc) -> Dict:
    """Process Type A document (Settimana A)."""
    classes_json = {}
    days_count = 5

    for page_num in range(len(doc)):
        page = doc[page_num]
        template_json = create_template_json(include_saturday=False)
        # Extract class name
        header = page.get_textbox(fitz.Rect(320, 20, 425, 50)).splitlines()
        class_name = re.sub(r'\s+', "", header[0])

        print(class_name)
        # Process each day
        for day_index in range(days_count):
            process_schedule_block(
                page, day_index, 60, 90, template_json, WEEKDAYS[day_index]
            )


        classes_json[class_name] = template_json

    return classes_json


def process_type_b(doc) -> Dict:
    """Process Type B document (Standard settimana B)."""
    classes_json = {}


    for page_num in range(len(doc)):
        page = doc[page_num]
        # Extract class name
        header = page.get_textbox(fitz.Rect(380, 20, 425, 50)).splitlines()
        class_name = re.sub(r'\s+', "", header[0])
        print(class_name)

        # Determine if Saturday is included
        days_count = 5 if "LIC" in class_name else 6
        template_json = create_template_json(include_saturday=(days_count == 6))

        # Process each day
        for day_index in range(days_count):
            process_schedule_block(
                page, day_index, 60, 80, template_json, WEEKDAYS[day_index]
            )
        classes_json[class_name] = template_json
    return classes_json


def process_type_c(doc) -> Dict:
    classes_json = {}
    days_count = 6
    page_num = 0
    class_name = "1"

    while "1" in class_name and page_num < len(doc):
        page = doc[page_num]

        header = page.get_textbox(fitz.Rect(300, 20, 350, 50)).splitlines()
        class_name = re.sub(r'\s+', "", header[0])

        if any(track in class_name for track in ["INF", "ELT", "MEC"]):
            template_json = create_template_json(include_saturday=True)

            for day_index in range(days_count):
                process_schedule_block(
                    page, day_index, 60, 90, template_json, WEEKDAYS[day_index]
                )

            classes_json[class_name] = template_json

        page_num += 1

    return classes_json


def save_json(data: Dict, filename_suffix: str) -> None:
    with open(f"orario_{filename_suffix}.json", "w") as outfile:
        json.dump(data, outfile, indent=4)


def main() -> None:

    if len(sys.argv) != 3:
        print("Usage: python orario_dumper.py <pdf_file_path> <type: a|b|c>")
        return

    file_path = sys.argv[1]

    if not exists(file_path):
        print("Error: File does not exist")
        return

    try:
        doc = fitz.open(file_path)

        if sys.argv[2] == TYPE_A:
            classes_json = process_type_a(doc)
        elif sys.argv[2] == TYPE_B:
            classes_json = process_type_b(doc)
        else:
            print("Unknown type")

        save_json(classes_json, sys.argv[2])
        print(f"Successfully processed document as Type {sys.argv[2]}")

    except Exception as e:
        print(f"Error processing file: {e}")
    finally:
        if 'doc' in locals():
            doc.close()


if __name__ == "__main__":
    main()