import h5py
import numpy as np
import pytest

from spectral_edge.utils.file_converter import split_hdf5_by_count, split_hdf5_by_time_slices


def _create_sample_split_input(path):
    with h5py.File(path, "w") as f:
        file_meta = f.create_group("metadata")
        file_meta.attrs["description"] = "test file"
        f.create_dataset("common_channels_mapping", data='{"accel_x": ["flight_001/channels/accel_x"]}')

        def add_flight(flight_key, accel_samples, temp_samples):
            flight = f.create_group(flight_key)
            metadata = flight.create_group("metadata")
            metadata.attrs["flight_id"] = flight_key

            channels = flight.create_group("channels")

            accel = channels.create_group("accel_x")
            accel.attrs["sample_rate"] = 10.0
            accel.attrs["units"] = "g"
            accel.create_dataset("data", data=np.arange(accel_samples, dtype=np.float64))
            accel.create_dataset("time", data=np.arange(accel_samples, dtype=np.float64) / 10.0)

            temp = channels.create_group("temp")
            temp.attrs["sample_rate"] = 5.0
            temp.attrs["units"] = "degC"
            temp.create_dataset("data", data=np.arange(temp_samples, dtype=np.float64))
            temp.create_dataset("time", data=np.arange(temp_samples, dtype=np.float64) / 5.0)

        add_flight("flight_001", accel_samples=100, temp_samples=50)  # 10.0s
        add_flight("flight_002", accel_samples=80, temp_samples=40)   # 8.0s


def test_split_hdf5_by_count_handles_non_flight_top_level_items(tmp_path):
    input_file = tmp_path / "input.h5"
    output_dir = tmp_path / "out_count"
    _create_sample_split_input(input_file)

    output_files = split_hdf5_by_count(str(input_file), str(output_dir), num_segments=4)

    assert len(output_files) == 4
    assert all(output_file.endswith(".hdf5") for output_file in output_files)

    for output_file in output_files:
        with h5py.File(output_file, "r") as f:
            assert "metadata" in f
            assert "common_channels_mapping" in f
            assert "flight_001" in f
            assert "flight_002" in f

            # Min duration across flights is 8.0s -> 2.0s per segment
            assert f["flight_001"]["metadata"].attrs["duration"] == pytest.approx(2.0)
            assert f["flight_002"]["metadata"].attrs["duration"] == pytest.approx(2.0)
            assert f["flight_001"]["metadata"].attrs["time_reference"] == "absolute"

            # Per-channel slicing must use each channel's sample rate.
            assert len(f["flight_001"]["channels"]["accel_x"]["data"]) == 20
            assert len(f["flight_001"]["channels"]["temp"]["data"]) == 10

    # Segment 2 should start at absolute time 2.0s.
    with h5py.File(output_files[1], "r") as f:
        accel_time = f["flight_001"]["channels"]["accel_x"]["time"]
        assert accel_time[0] == pytest.approx(2.0)
        assert f["flight_001"]["channels"]["accel_x"].attrs["start_time"] == pytest.approx(2.0)


def test_split_hdf5_by_time_slices_handles_non_flight_top_level_items(tmp_path):
    input_file = tmp_path / "input.h5"
    output_dir = tmp_path / "out_slices"
    _create_sample_split_input(input_file)

    output_files = split_hdf5_by_time_slices(
        str(input_file),
        str(output_dir),
        time_slices=[(1.0, 3.0), (3.0, 5.0)],
    )

    assert len(output_files) == 2
    assert all(output_file.endswith(".hdf5") for output_file in output_files)

    with h5py.File(output_files[0], "r") as f:
        assert len(f["flight_001"]["channels"]["accel_x"]["data"]) == 20
        assert len(f["flight_001"]["channels"]["temp"]["data"]) == 10
        assert f["flight_001"]["channels"]["accel_x"]["time"][0] == pytest.approx(1.0)
        assert f["flight_001"]["metadata"].attrs["split_start_time"] == pytest.approx(1.0)


def test_split_hdf5_by_time_slices_validates_against_common_duration(tmp_path):
    input_file = tmp_path / "input.h5"
    output_dir = tmp_path / "out_invalid"
    _create_sample_split_input(input_file)

    with pytest.raises(ValueError, match="exceeds available duration"):
        split_hdf5_by_time_slices(
            str(input_file),
            str(output_dir),
            time_slices=[(0.0, 9.0)],  # flight_002 is only 8.0s
        )
