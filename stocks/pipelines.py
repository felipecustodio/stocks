import re
import datetime as dt

class NormalizeValuesPipeline:
    def parse_float(self, value):
        """Convert a Brazilian formatted float string to a Python float."""
        if not value or value in {"-", "\n-"}:
            return None
        # Remove any unwanted characters and replace comma with dot
        value = re.sub(r"[^\d,.-]", "", value)
        value = value.replace(".", "").replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None

    def parse_percentage(self, value):
        """Convert a percentage string to a Python float."""
        if not value or value in {"-", "\n-"}:
            return None
        # Remove unwanted characters and extract percentage
        value = re.sub(r"[^\d,.-]", "", value)
        value = value.replace(".", "").replace(",", ".")
        try:
            return float(value) / 100
        except ValueError:
            return None

    def process_dictionary(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, str):
                if "%" in value:
                    dictionary[key] = self.parse_percentage(value)
                else:
                    # If it starts with a number or "-", and does not have "/" (date), convert to float
                    if re.match(r"^-?\d", value) and "/" not in value:
                        dictionary[key] = self.parse_float(value)
            if isinstance(value, dict):
                self.process_dictionary(value)
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item)
        return item

class CleanValuesPipeline:
    def process_dictionary(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, str):
                dictionary[key] = value.strip()
                dictionary[key] = value.replace("\n", "")
            elif isinstance(value, dict):
                self.process_dictionary(value)
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item)
        return item

class NanValuesPipeline:
    def process_dictionary(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                self.process_dictionary(value)
            elif value in {"", "-", None}:
                dictionary[key] = None
            elif key in ["Papel", "Tipo", "Empresa", "Setor", "Subsetor", "Data últ cot"] and not value:
                dictionary[key] = None
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item)
        return item

class DateValuesPipeline:
    def process_dictionary(self, dictionary, spider):
        for key, value in dictionary.items():
            if key in ["Data últ cot", "Data", "Últ balanço processado"] and value is not None and value != "-":
                try:
                    dictionary[key] = dt.datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception as e:
                    spider.logger.error(f"Error parsing date: {e}")
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item, spider)
        return item