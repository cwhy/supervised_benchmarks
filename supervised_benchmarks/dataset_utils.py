from pathlib import Path
from typing import List, Tuple, Literal, Dict
from urllib.error import URLError

from supervised_benchmarks.download_utils import download_and_extract_archive, check_integrity
from supervised_benchmarks.dataset_protocols import SupportedDatasetNames, Port, DataPool, Subset

DataPath = Literal['processed', 'cache', 'raw']
StorageType = Literal['array_dict']


def subset_all(pool_dict: Dict[Port, DataPool], subset: Subset):
    return {port: pool.subset(subset) for port, pool in pool_dict.items()}


def get_data_dir(base_path: Path, data_name: str, sub_path: DataPath) -> Path:
    data_path = base_path.joinpath(data_name)
    data_path.mkdir(exist_ok=True)
    _path = data_path.joinpath(sub_path)
    _path.mkdir(exist_ok=True)
    return _path


def download_resources(base_path: Path, name: SupportedDatasetNames, resources: List[Tuple[str, str]],
                       mirrors: List[str]) -> None:
    raw_path = get_data_dir(base_path, name, 'raw')

    def _check_exists() -> bool:
        return all(
            check_integrity(raw_path.joinpath(file_name))
            for file_name, _ in resources
        )

    if _check_exists():
        return None
    for filename, md5 in resources:
        for mirror in mirrors:
            url = "{}{}".format(mirror, filename)
            try:
                print("Downloading {}".format(url))
                download_and_extract_archive(
                    url, download_root=raw_path,
                    filename=filename,
                    md5=md5
                )
            except URLError as error:
                print(
                    "Failed to download (trying next):\n{}".format(error)
                )
                continue
            finally:
                print()
            break
        else:
            raise RuntimeError("Error downloading {}".format(filename))
