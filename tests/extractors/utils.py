import csv
import io


def test_data_dicts(test_data: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(test_data)))
