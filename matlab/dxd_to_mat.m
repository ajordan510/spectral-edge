function dxd_to_mat(input_file, output_file, varargin)
% DXD_TO_MAT Convert DEWESoft .dxd files to MATLAB .mat format
%
% This function converts DEWESoft data files (.dxd or .dxz format) to MATLAB
% .mat format using the official DEWESoft Data Reader Library.
%
% SYNTAX:
%   dxd_to_mat(input_file, output_file)
%   dxd_to_mat(input_file, output_file, 'channels', channel_list)
%   dxd_to_mat(input_file, output_file, 'max_samples', max_samples)
%   dxd_to_mat(input_file, output_file, 'format', format_version)
%
% INPUTS:
%   input_file   - Path to input .dxd or .dxz file (string)
%   output_file  - Path to output .mat file (string)
%
% OPTIONAL NAME-VALUE PAIRS:
%   'channels'    - Cell array of channel names to export (default: all channels)
%   'max_samples' - Maximum number of samples per channel (default: all samples)
%   'format'      - MAT file format: '-v7.3' (HDF5, large files) or '-v7' (default)
%
% EXAMPLES:
%   % Convert all channels to MAT file
%   dxd_to_mat('data/flight_test.dxd', 'output/flight_test.mat');
%
%   % Convert specific channels only
%   channels = {'Accel_X', 'Accel_Y', 'Accel_Z'};
%   dxd_to_mat('data/vibration.dxd', 'output/vibration.mat', 'channels', channels);
%
%   % Limit to first 10000 samples per channel
%   dxd_to_mat('data/large_file.dxd', 'output/preview.mat', 'max_samples', 10000);
%
%   % Use HDF5-based format for large files (> 2 GB)
%   dxd_to_mat('data/huge_file.dxd', 'output/huge_file.mat', 'format', '-v7.3');
%
% OUTPUT STRUCTURE:
%   The output .mat file contains a structure named 'dewesoft_data' with fields:
%     metadata    - Structure with file metadata (sample_rate, duration, etc.)
%     channels    - Structure array with channel data:
%                   .name        - Channel name
%                   .unit        - Engineering unit
%                   .description - Channel description
%                   .data_type   - Data type name
%                   .timestamps  - Time vector (seconds)
%                   .values      - Data values
%
% REQUIREMENTS:
%   - MATLAB R2018b or later
%   - DEWESoft Data Reader Library (included in dewesoft/ directory)
%   - DWDataReader.m wrapper class (included in dewesoft/ directory)
%
% AUTHOR:
%   SpectralEdge Development Team
%
% LICENSE:
%   MIT License
%
% SEE ALSO:
%   load, save, DWDataReader

    %% Parse Input Arguments
    % Create input parser to handle optional arguments
    p = inputParser;
    
    % Required arguments
    addRequired(p, 'input_file', @ischar);
    addRequired(p, 'output_file', @ischar);
    
    % Optional name-value pairs
    addParameter(p, 'channels', {}, @iscell);  % Cell array of channel names
    addParameter(p, 'max_samples', [], @isnumeric);  % Maximum samples per channel
    addParameter(p, 'format', '-v7', @ischar);  % MAT file format
    
    % Parse the inputs
    parse(p, input_file, output_file, varargin{:});
    
    % Extract parsed values
    input_file = p.Results.input_file;
    output_file = p.Results.output_file;
    selected_channel_names = p.Results.channels;
    max_samples = p.Results.max_samples;
    mat_format = p.Results.format;
    
    %% Display Script Header
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' DEWESoft DXD to MAT Converter\n');
    fprintf('======================================================================\n');
    fprintf('This script converts DEWESoft data files to MATLAB .mat format\n');
    fprintf('using the official DEWESoft Data Reader Library.\n');
    fprintf('\n');
    
    %% Validate Input File
    fprintf('Validating input file...\n');
    
    % Check if file exists
    if ~exist(input_file, 'file')
        error('Input file does not exist: %s', input_file);
    end
    
    % Check file extension
    [~, ~, ext] = fileparts(input_file);
    if ~ismember(lower(ext), {'.dxd', '.dxz'})
        warning('File extension ''%s'' is not .dxd or .dxz', ext);
        fprintf('The file may not be a valid DEWESoft data file.\n');
    end
    
    fprintf('✓ Input file validated\n');
    
    %% Add DEWESoft Library to Path
    % Get the directory containing this script
    script_path = fileparts(mfilename('fullpath'));
    dewesoft_path = fullfile(script_path, 'dewesoft');
    
    % Add to MATLAB path temporarily
    addpath(dewesoft_path);
    
    % Ensure the path is removed when function exits (even on error)
    cleanup_obj = onCleanup(@() rmpath(dewesoft_path));
    
    %% Create DWDataReader Object
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' Loading DEWESoft Data Reader Library\n');
    fprintf('======================================================================\n');
    
    try
        % Create reader object (this loads the library)
        reader = DWDataReader();
        fprintf('✓ Library loaded successfully\n');
    catch ME
        fprintf('ERROR: Failed to load DEWESoft Data Reader Library\n');
        fprintf('Details: %s\n', ME.message);
        fprintf('\nMake sure the library files are in: %s\n', dewesoft_path);
        fprintf('Required files:\n');
        fprintf('  - Windows 64-bit: DWDataReaderLib64.dll\n');
        fprintf('  - Linux 64-bit: DWDataReaderLib64.so\n');
        fprintf('  - Header files: DWDataReaderLibFuncs.h, etc.\n');
        rethrow(ME);
    end
    
    %% Open DXD File
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' Opening File\n');
    fprintf('======================================================================\n');
    fprintf('Input file: %s\n', input_file);
    
    try
        [success, file_info] = reader.openFile(input_file);
        if ~success
            error('Failed to open file: %s', input_file);
        end
        fprintf('✓ File opened successfully\n');
    catch ME
        fprintf('ERROR: Failed to open file\n');
        fprintf('Details: %s\n', ME.message);
        rethrow(ME);
    end
    
    %% Get File Metadata
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' File Metadata\n');
    fprintf('======================================================================\n');
    
    try
        % Get measurement information
        [success, meas_info] = reader.getMeasurementInfo();
        if ~success
            error('Failed to get measurement info');
        end
        
        % Display metadata
        fprintf('Sample Rate:         %.2f Hz\n', meas_info.sample_rate);
        fprintf('Start Measure Time:  %.6f s\n', meas_info.start_measure_time);
        fprintf('Start Store Time:    %.6f s\n', meas_info.start_store_time);
        fprintf('Duration:            %.2f s\n', meas_info.duration);
        
        % Store metadata for output
        metadata = struct();
        metadata.sample_rate = meas_info.sample_rate;
        metadata.start_measure_time = meas_info.start_measure_time;
        metadata.start_store_time = meas_info.start_store_time;
        metadata.duration = meas_info.duration;
        metadata.input_file = input_file;
        metadata.conversion_date = datestr(now);
        
    catch ME
        fprintf('ERROR: Failed to get metadata\n');
        fprintf('Details: %s\n', ME.message);
        rethrow(ME);
    end
    
    %% Get Channel List
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' Available Channels\n');
    fprintf('======================================================================\n');
    
    try
        % Get list of all channels
        [success, channel_list] = reader.getChannelList();
        if ~success
            error('Failed to get channel list');
        end
        
        num_channels = length(channel_list);
        fprintf('Total channels: %d\n', num_channels);
        
        % Display channel information
        fprintf('\nChannel List:\n');
        fprintf('%-8s %-30s %-15s %-15s\n', 'Index', 'Name', 'Unit', 'Type');
        fprintf('%s\n', repmat('-', 1, 70));
        
        for i = 1:num_channels
            ch = channel_list(i);
            fprintf('%-8d %-30s %-15s %-15s\n', ...
                    ch.index, ch.name, ch.unit, ch.data_type_name);
        end
        
    catch ME
        fprintf('ERROR: Failed to get channel list\n');
        fprintf('Details: %s\n', ME.message);
        rethrow(ME);
    end
    
    %% Select Channels to Export
    % If specific channels were requested, filter the list
    if ~isempty(selected_channel_names)
        fprintf('\nFiltering channels...\n');
        
        % Find matching channels
        selected_indices = [];
        for i = 1:length(selected_channel_names)
            requested_name = selected_channel_names{i};
            found = false;
            
            for j = 1:num_channels
                if strcmp(channel_list(j).name, requested_name)
                    selected_indices(end+1) = j; %#ok<AGROW>
                    found = true;
                    break;
                end
            end
            
            if ~found
                warning('Channel ''%s'' not found in file', requested_name);
            end
        end
        
        if isempty(selected_indices)
            error('No valid channels selected');
        end
        
        % Filter channel list
        channel_list = channel_list(selected_indices);
        num_channels = length(channel_list);
        
        fprintf('Exporting %d selected channel(s):\n', num_channels);
        for i = 1:num_channels
            fprintf('  - %s\n', channel_list(i).name);
        end
    else
        fprintf('\nExporting all %d channels\n', num_channels);
    end
    
    %% Read Channel Data
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' Reading Channel Data\n');
    fprintf('======================================================================\n');
    
    % Initialize structure array to hold channel data
    channels = struct('name', {}, 'unit', {}, 'description', {}, ...
                      'data_type', {}, 'timestamps', {}, 'values', {});
    
    try
        % Loop through each selected channel
        for i = 1:num_channels
            ch = channel_list(i);
            
            fprintf('\nReading channel %d/%d: %s\n', i, num_channels, ch.name);
            
            % Get scaled samples for this channel
            [success, timestamps, values] = reader.getScaledSamples(ch.index);
            if ~success
                warning('Failed to read channel: %s', ch.name);
                continue;
            end
            
            % Apply sample limit if requested
            if ~isempty(max_samples) && length(timestamps) > max_samples
                fprintf('  Limiting to first %d samples (file has %d)\n', ...
                        max_samples, length(timestamps));
                timestamps = timestamps(1:max_samples);
                values = values(1:max_samples);
            end
            
            fprintf('  Samples read: %d\n', length(timestamps));
            
            % Store channel data in structure
            channels(i).name = ch.name;
            channels(i).unit = ch.unit;
            channels(i).description = ch.description;
            channels(i).data_type = ch.data_type_name;
            channels(i).timestamps = timestamps;
            channels(i).values = values;
        end
        
        fprintf('\n✓ All channel data read successfully\n');
        
    catch ME
        fprintf('ERROR: Failed to read channel data\n');
        fprintf('Details: %s\n', ME.message);
        rethrow(ME);
    end
    
    %% Close File
    fprintf('\nClosing file...\n');
    try
        reader.close();
        fprintf('✓ File closed\n');
    catch ME
        warning('Error closing file: %s', ME.message);
    end
    
    %% Save to MAT File
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' Writing MAT File\n');
    fprintf('======================================================================\n');
    fprintf('Output file: %s\n', output_file);
    fprintf('Format: %s\n', mat_format);
    
    try
        % Create output directory if it doesn't exist
        output_dir = fileparts(output_file);
        if ~isempty(output_dir) && ~exist(output_dir, 'dir')
            mkdir(output_dir);
            fprintf('Created output directory: %s\n', output_dir);
        end
        
        % Create the main data structure
        dewesoft_data = struct();
        dewesoft_data.metadata = metadata;
        dewesoft_data.channels = channels;
        
        % Save to MAT file
        % Note: Use -v7.3 format for files larger than 2 GB
        save(output_file, 'dewesoft_data', mat_format);
        
        fprintf('✓ MAT file written successfully\n');
        
        % Display file information
        file_info_struct = dir(output_file);
        file_size_mb = file_info_struct.bytes / (1024 * 1024);
        fprintf('  File size: %.2f MB\n', file_size_mb);
        fprintf('  Channels: %d\n', length(channels));
        
    catch ME
        fprintf('ERROR: Failed to write MAT file\n');
        fprintf('Details: %s\n', ME.message);
        rethrow(ME);
    end
    
    %% Display Success Message
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' Conversion Complete\n');
    fprintf('======================================================================\n');
    fprintf('✓ Successfully converted %s\n', input_file);
    fprintf('✓ Output saved to %s\n', output_file);
    fprintf('✓ Exported %d channel(s)\n', num_channels);
    fprintf('\n');
    
    %% Display Usage Instructions
    fprintf('To load the data in MATLAB:\n');
    fprintf('  >> data = load(''%s'');\n', output_file);
    fprintf('  >> metadata = data.dewesoft_data.metadata;\n');
    fprintf('  >> channels = data.dewesoft_data.channels;\n');
    fprintf('\n');
    fprintf('To access a specific channel (e.g., first channel):\n');
    fprintf('  >> ch1 = channels(1);\n');
    fprintf('  >> plot(ch1.timestamps, ch1.values);\n');
    fprintf('  >> xlabel(''Time (s)'');\n');
    fprintf('  >> ylabel(sprintf(''%%s (%%s)'', ch1.name, ch1.unit));\n');
    fprintf('\n');

end


%% Helper Function: Display Error Message
function display_error(ME)
    % Display a formatted error message
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf(' ERROR\n');
    fprintf('======================================================================\n');
    fprintf('An error occurred during conversion:\n');
    fprintf('  Message: %s\n', ME.message);
    fprintf('  Location: %s (line %d)\n', ME.stack(1).name, ME.stack(1).line);
    fprintf('\n');
    fprintf('Stack trace:\n');
    for i = 1:length(ME.stack)
        fprintf('  %d. %s (line %d)\n', i, ME.stack(i).name, ME.stack(i).line);
    end
    fprintf('======================================================================\n');
end
