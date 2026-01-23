function convert_to_hdf5(output_filename, flight_data)
% CONVERT_TO_HDF5 Convert MATLAB data to SpectralEdge HDF5 format
%
% This function converts MATLAB flight test data into the HDF5 format
% expected by SpectralEdge for PSD analysis and visualization.
%
% SYNTAX:
%   convert_to_hdf5(output_filename, flight_data)
%
% INPUTS:
%   output_filename - String, path to output HDF5 file (e.g., 'test_data.h5')
%   flight_data     - Struct or cell array of structs containing flight data
%
% FLIGHT DATA STRUCTURE:
%   Each flight struct must contain:
%     .flight_id    - String, unique flight identifier (e.g., 'Flight_001')
%     .date         - String, date of flight (e.g., '2025-01-22')
%     .description  - String, flight description (optional)
%     .channels     - Struct with channel data
%
%   Each channel in .channels must contain:
%     .data         - Vector of signal data (1D array)
%     .sample_rate  - Scalar, sampling rate in Hz
%     .units        - String, measurement units (e.g., 'g', 'm/s^2', 'V')
%     .start_time   - Scalar, start time in seconds (default: 0.0)
%     .description  - String, channel description (optional)
%     .sensor_id    - String, sensor identifier (optional)
%     .location     - String, sensor location (optional)
%
% EXAMPLE 1: Single Flight, Single Channel
%   flight.flight_id = 'Test_Flight_001';
%   flight.date = '2025-01-22';
%   flight.description = 'Vibration test';
%   flight.channels.accel_x.data = randn(10000, 1);  % 10k samples
%   flight.channels.accel_x.sample_rate = 1000;      % 1 kHz
%   flight.channels.accel_x.units = 'g';
%   flight.channels.accel_x.start_time = 0.0;
%   
%   convert_to_hdf5('test_data.h5', flight);
%
% EXAMPLE 2: Single Flight, Multiple Channels
%   flight.flight_id = 'Flight_001';
%   flight.date = '2025-01-22';
%   flight.description = 'Multi-axis vibration test';
%   
%   % X-axis accelerometer
%   flight.channels.accel_x.data = randn(50000, 1);
%   flight.channels.accel_x.sample_rate = 5000;
%   flight.channels.accel_x.units = 'g';
%   flight.channels.accel_x.start_time = 0.0;
%   flight.channels.accel_x.description = 'X-axis acceleration';
%   flight.channels.accel_x.location = 'Wing tip';
%   
%   % Y-axis accelerometer
%   flight.channels.accel_y.data = randn(50000, 1);
%   flight.channels.accel_y.sample_rate = 5000;
%   flight.channels.accel_y.units = 'g';
%   flight.channels.accel_y.start_time = 0.0;
%   flight.channels.accel_y.description = 'Y-axis acceleration';
%   flight.channels.accel_y.location = 'Wing tip';
%   
%   % Z-axis accelerometer
%   flight.channels.accel_z.data = randn(50000, 1);
%   flight.channels.accel_z.sample_rate = 5000;
%   flight.channels.accel_z.units = 'g';
%   flight.channels.accel_z.start_time = 0.0;
%   flight.channels.accel_z.description = 'Z-axis acceleration';
%   flight.channels.accel_z.location = 'Wing tip';
%   
%   convert_to_hdf5('multi_channel.h5', flight);
%
% EXAMPLE 3: Multiple Flights
%   % Flight 1
%   flights{1}.flight_id = 'Flight_001';
%   flights{1}.date = '2025-01-22';
%   flights{1}.channels.accel_x.data = randn(10000, 1);
%   flights{1}.channels.accel_x.sample_rate = 1000;
%   flights{1}.channels.accel_x.units = 'g';
%   flights{1}.channels.accel_x.start_time = 0.0;
%   
%   % Flight 2
%   flights{2}.flight_id = 'Flight_002';
%   flights{2}.date = '2025-01-23';
%   flights{2}.channels.accel_x.data = randn(15000, 1);
%   flights{2}.channels.accel_x.sample_rate = 1000;
%   flights{2}.channels.accel_x.units = 'g';
%   flights{2}.channels.accel_x.start_time = 0.0;
%   
%   convert_to_hdf5('multiple_flights.h5', flights);
%
% NOTES:
%   - Data vectors must be 1D (column or row vectors)
%   - Sample rate must be positive
%   - Units string is required for proper labeling in SpectralEdge
%   - Channel names will be used as-is in the GUI
%   - Flight groups are named 'flight_001', 'flight_002', etc.
%
% SEE ALSO: h5create, h5write, h5writeatt
%
% Author: SpectralEdge Development Team
% Date: 2025-01-22

    % Input validation
    if nargin < 2
        error('convert_to_hdf5:InvalidInput', ...
              'Usage: convert_to_hdf5(output_filename, flight_data)');
    end
    
    % Delete existing file if it exists
    if exist(output_filename, 'file')
        delete(output_filename);
        fprintf('Deleted existing file: %s\n', output_filename);
    end
    
    % Convert single flight struct to cell array
    if isstruct(flight_data)
        flight_data = {flight_data};
    end
    
    % Validate flight_data is cell array
    if ~iscell(flight_data)
        error('convert_to_hdf5:InvalidInput', ...
              'flight_data must be a struct or cell array of structs');
    end
    
    fprintf('Converting %d flight(s) to HDF5 format...\n', length(flight_data));
    
    % Process each flight
    for flight_idx = 1:length(flight_data)
        flight = flight_data{flight_idx};
        
        % Validate flight structure
        if ~isfield(flight, 'flight_id')
            error('convert_to_hdf5:MissingField', ...
                  'Flight %d missing required field: flight_id', flight_idx);
        end
        if ~isfield(flight, 'channels')
            error('convert_to_hdf5:MissingField', ...
                  'Flight %d missing required field: channels', flight_idx);
        end
        
        % Create flight group name
        flight_group = sprintf('flight_%03d', flight_idx);
        fprintf('\nProcessing %s (%s)...\n', flight_group, flight.flight_id);
        
        % Write flight metadata
        write_flight_metadata(output_filename, flight_group, flight);
        
        % Process each channel
        channel_names = fieldnames(flight.channels);
        fprintf('  Channels: %d\n', length(channel_names));
        
        for ch_idx = 1:length(channel_names)
            channel_name = channel_names{ch_idx};
            channel = flight.channels.(channel_name);
            
            % Validate channel structure
            validate_channel(channel, channel_name, flight_idx);
            
            % Write channel data and attributes
            write_channel_data(output_filename, flight_group, channel_name, channel);
            
            fprintf('    - %s: %d samples @ %.0f Hz (%s)\n', ...
                    channel_name, length(channel.data), ...
                    channel.sample_rate, channel.units);
        end
    end
    
    fprintf('\nHDF5 file created successfully: %s\n', output_filename);
    fprintf('File size: %.2f MB\n', get_file_size_mb(output_filename));
end


function write_flight_metadata(filename, flight_group, flight)
    % Write flight-level metadata
    
    % Create metadata group
    meta_group = sprintf('/%s/metadata', flight_group);
    
    % Write flight_id attribute
    h5writeatt(filename, meta_group, 'flight_id', flight.flight_id);
    
    % Write date attribute
    if isfield(flight, 'date')
        h5writeatt(filename, meta_group, 'date', flight.date);
    else
        h5writeatt(filename, meta_group, 'date', datestr(now, 'yyyy-mm-dd'));
    end
    
    % Calculate and write duration
    channel_names = fieldnames(flight.channels);
    if ~isempty(channel_names)
        first_channel = flight.channels.(channel_names{1});
        duration = length(first_channel.data) / first_channel.sample_rate;
        h5writeatt(filename, meta_group, 'duration', duration);
    else
        h5writeatt(filename, meta_group, 'duration', 0.0);
    end
    
    % Write description attribute
    if isfield(flight, 'description')
        h5writeatt(filename, meta_group, 'description', flight.description);
    else
        h5writeatt(filename, meta_group, 'description', '');
    end
end


function write_channel_data(filename, flight_group, channel_name, channel)
    % Write channel data and attributes
    
    % Ensure data is column vector
    data = channel.data(:);
    
    % Create dataset path
    dataset_path = sprintf('/%s/channels/%s', flight_group, channel_name);
    
    % Create and write dataset
    h5create(filename, dataset_path, size(data), 'Datatype', 'double');
    h5write(filename, dataset_path, data);
    
    % Write required attributes
    h5writeatt(filename, dataset_path, 'units', channel.units);
    h5writeatt(filename, dataset_path, 'sample_rate', channel.sample_rate);
    
    if isfield(channel, 'start_time')
        h5writeatt(filename, dataset_path, 'start_time', channel.start_time);
    else
        h5writeatt(filename, dataset_path, 'start_time', 0.0);
    end
    
    % Write optional attributes
    if isfield(channel, 'description')
        h5writeatt(filename, dataset_path, 'description', channel.description);
    else
        h5writeatt(filename, dataset_path, 'description', '');
    end
    
    if isfield(channel, 'sensor_id')
        h5writeatt(filename, dataset_path, 'sensor_id', channel.sensor_id);
    else
        h5writeatt(filename, dataset_path, 'sensor_id', '');
    end
    
    if isfield(channel, 'location')
        h5writeatt(filename, dataset_path, 'location', channel.location);
    else
        h5writeatt(filename, dataset_path, 'location', '');
    end
    
    if isfield(channel, 'range_min')
        h5writeatt(filename, dataset_path, 'range_min', channel.range_min);
    end
    
    if isfield(channel, 'range_max')
        h5writeatt(filename, dataset_path, 'range_max', channel.range_max);
    end
end


function validate_channel(channel, channel_name, flight_idx)
    % Validate channel structure
    
    if ~isfield(channel, 'data')
        error('convert_to_hdf5:MissingField', ...
              'Flight %d, channel %s missing required field: data', ...
              flight_idx, channel_name);
    end
    
    if ~isfield(channel, 'sample_rate')
        error('convert_to_hdf5:MissingField', ...
              'Flight %d, channel %s missing required field: sample_rate', ...
              flight_idx, channel_name);
    end
    
    if ~isfield(channel, 'units')
        error('convert_to_hdf5:MissingField', ...
              'Flight %d, channel %s missing required field: units', ...
              flight_idx, channel_name);
    end
    
    % Validate data is numeric vector
    if ~isnumeric(channel.data) || ~isvector(channel.data)
        error('convert_to_hdf5:InvalidData', ...
              'Flight %d, channel %s: data must be a numeric vector', ...
              flight_idx, channel_name);
    end
    
    % Validate sample rate is positive
    if channel.sample_rate <= 0
        error('convert_to_hdf5:InvalidSampleRate', ...
              'Flight %d, channel %s: sample_rate must be positive', ...
              flight_idx, channel_name);
    end
end


function size_mb = get_file_size_mb(filename)
    % Get file size in MB
    file_info = dir(filename);
    size_mb = file_info.bytes / (1024 * 1024);
end
