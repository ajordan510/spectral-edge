import re

import h5py
import numpy as np
from scipy.io import loadmat

from spectral_edge.utils.file_converter import convert_hdf5_to_marvin_mat


REQUIRED_FIELDS = {"amp", "t", "sr", "source", "units", "name", "desc"}


def _text_from_mat(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    if isinstance(value, np.generic):
        return _text_from_mat(value.item())
    if isinstance(value, np.ndarray):
        if value.dtype.kind in {"U", "S"}:
            return "".join(value.astype(str).flatten().tolist())
        if value.size == 1:
            return _text_from_mat(value.item())
    return str(value)


def _load_single_marvin_struct(mat_path):
    mat_data = loadmat(mat_path, struct_as_record=False, squeeze_me=False)
    user_vars = [key for key in mat_data.keys() if not key.startswith("__")]
    assert len(user_vars) == 1

    var_name = user_vars[0]
    struct_obj = mat_data[var_name][0, 0]
    field_dict = {field: getattr(struct_obj, field) for field in struct_obj._fieldnames}
    return var_name, field_dict


def _create_multi_flight_input(path):
    with h5py.File(path, "w") as h5_file:
        def add_flight(flight_key, channel_defs):
            flight_group = h5_file.create_group(flight_key)
            metadata_group = flight_group.create_group("metadata")
            metadata_group.attrs["flight_id"] = flight_key

            channels_group = flight_group.create_group("channels")
            for channel_name, sample_rate, units in channel_defs:
                channel_group = channels_group.create_group(channel_name)
                data = np.linspace(0.0, 1.0, 20, dtype=np.float64)
                time = np.arange(20, dtype=np.float64) / sample_rate
                channel_group.create_dataset("data", data=data)
                channel_group.create_dataset("time", data=time)
                channel_group.attrs["sample_rate"] = sample_rate
                channel_group.attrs["units"] = units
                channel_group.attrs["description"] = f"{channel_name} description"

        add_flight(
            "flight_001",
            [
                ("temp sensor-1", 100.0, "degC"),
                ("1-invalid#chan", 50.0, "g"),
            ],
        )
        add_flight(
            "flight_002",
            [
                ("temp sensor-1", 100.0, "degC"),
                ("1-invalid#chan", 50.0, "g"),
            ],
        )


def _create_missing_time_input(path):
    with h5py.File(path, "w") as h5_file:
        flight_group = h5_file.create_group("flight_001")
        flight_group.create_group("metadata")
        channels_group = flight_group.create_group("channels")

        channel_group = channels_group.create_group("temperature")
        channel_group.create_dataset("data", data=np.arange(10, dtype=np.float64))
        channel_group.attrs["sample_rate"] = 5.0
        channel_group.attrs["start_time"] = 3.0
        channel_group.attrs["units"] = "degC"


def _create_missing_units_input(path):
    with h5py.File(path, "w") as h5_file:
        flight_group = h5_file.create_group("flight_001")
        flight_group.create_group("metadata")
        channels_group = flight_group.create_group("channels")

        channel_group = channels_group.create_group("no_units_channel")
        channel_group.create_dataset("data", data=np.arange(8, dtype=np.float64))
        channel_group.create_dataset("time", data=np.arange(8, dtype=np.float64) * 0.1)
        channel_group.attrs["sample_rate"] = 10.0


def test_convert_hdf5_to_marvin_mat_multi_flight_multi_channel(tmp_path):
    input_path = tmp_path / "input_multi.hdf5"
    output_dir = tmp_path / "out"
    _create_multi_flight_input(input_path)

    output_files = convert_hdf5_to_marvin_mat(str(input_path), str(output_dir))

    assert len(output_files) == 4
    assert all(path.endswith(".mat") for path in output_files)

    for mat_path in output_files:
        var_name, marvin_struct = _load_single_marvin_struct(mat_path)

        assert re.match(r"^[A-Za-z][A-Za-z0-9_]*$", var_name)
        assert REQUIRED_FIELDS.issubset(set(marvin_struct.keys()))

        amp = np.asarray(marvin_struct["amp"])
        time = np.asarray(marvin_struct["t"])
        assert amp.ndim == 2 and amp.shape[1] == 1
        assert time.ndim == 2 and time.shape[1] == 1
        assert amp.shape[0] == time.shape[0]

        source_text = _text_from_mat(marvin_struct["source"])
        units_text = _text_from_mat(marvin_struct["units"])
        desc_text = _text_from_mat(marvin_struct["desc"])

        assert source_text == "MARVIN"
        assert units_text in {"degC", "g"}
        assert desc_text == input_path.name


def test_convert_hdf5_to_marvin_mat_missing_time_uses_start_time_and_sample_rate(tmp_path):
    input_path = tmp_path / "input_missing_time.hdf5"
    output_dir = tmp_path / "out"
    _create_missing_time_input(input_path)

    output_files = convert_hdf5_to_marvin_mat(str(input_path), str(output_dir))
    assert len(output_files) == 1

    _, marvin_struct = _load_single_marvin_struct(output_files[0])
    time = np.asarray(marvin_struct["t"], dtype=np.float64)
    assert time.shape == (10, 1)
    assert time[0, 0] == 3.0
    assert time[1, 0] == 3.2
    assert float(np.asarray(marvin_struct["sr"]).reshape(-1)[0]) == 5.0


def test_convert_hdf5_to_marvin_mat_missing_units_still_writes_required_units_field(tmp_path):
    input_path = tmp_path / "input_missing_units.hdf5"
    output_dir = tmp_path / "out"
    _create_missing_units_input(input_path)

    output_files = convert_hdf5_to_marvin_mat(str(input_path), str(output_dir))
    assert len(output_files) == 1

    _, marvin_struct = _load_single_marvin_struct(output_files[0])
    assert "units" in marvin_struct
    assert _text_from_mat(marvin_struct["units"]) == ""
