% EXAMPLE_CONVERSION - Examples of converting MATLAB data to HDF5 for SpectralEdge
%
% This script demonstrates various ways to convert your MATLAB flight test
% data into the HDF5 format expected by SpectralEdge.
%
% Author: SpectralEdge Development Team
% Date: 2025-01-22

%% Example 1: Simple Single Channel Test Data
% Perfect for quick testing

fprintf('=== Example 1: Simple Single Channel ===\n');

% Create synthetic vibration data
duration = 10;  % seconds
fs = 1000;      % 1 kHz sample rate
t = (0:1/fs:duration-1/fs)';
signal = sin(2*pi*50*t) + 0.5*sin(2*pi*120*t) + 0.1*randn(size(t));

% Package into flight structure
flight.flight_id = 'Test_Flight_001';
flight.date = datestr(now, 'yyyy-mm-dd');
flight.description = 'Simple sinusoidal test signal';
flight.channels.test_signal.data = signal;
flight.channels.test_signal.sample_rate = fs;
flight.channels.test_signal.units = 'g';
flight.channels.test_signal.start_time = 0.0;
flight.channels.test_signal.description = '50 Hz + 120 Hz sine waves with noise';

% Convert to HDF5
convert_to_hdf5('example1_simple.h5', flight);

fprintf('Created: example1_simple.h5\n\n');


%% Example 2: Multi-Axis Accelerometer Data
% Typical for vibration testing with triaxial accelerometers

fprintf('=== Example 2: Multi-Axis Accelerometer ===\n');

% Simulation parameters
duration = 30;   % 30 seconds
fs = 5000;       % 5 kHz sample rate
t = (0:1/fs:duration-1/fs)';
n_samples = length(t);

% Generate realistic accelerometer signals
% X-axis: dominant frequency at 100 Hz
accel_x = 0.5*sin(2*pi*100*t) + 0.2*sin(2*pi*250*t) + 0.05*randn(n_samples, 1);

% Y-axis: dominant frequency at 150 Hz
accel_y = 0.3*sin(2*pi*150*t) + 0.15*sin(2*pi*300*t) + 0.05*randn(n_samples, 1);

% Z-axis: dominant frequency at 80 Hz
accel_z = 0.6*sin(2*pi*80*t) + 0.25*sin(2*pi*200*t) + 0.05*randn(n_samples, 1);

% Package into flight structure
flight.flight_id = 'Vibration_Test_001';
flight.date = '2025-01-22';
flight.description = 'Triaxial vibration test - wing tip sensor';

% X-axis channel
flight.channels.accel_x.data = accel_x;
flight.channels.accel_x.sample_rate = fs;
flight.channels.accel_x.units = 'g';
flight.channels.accel_x.start_time = 0.0;
flight.channels.accel_x.description = 'X-axis acceleration';
flight.channels.accel_x.sensor_id = 'ACC_001';
flight.channels.accel_x.location = 'Wing tip - starboard';

% Y-axis channel
flight.channels.accel_y.data = accel_y;
flight.channels.accel_y.sample_rate = fs;
flight.channels.accel_y.units = 'g';
flight.channels.accel_y.start_time = 0.0;
flight.channels.accel_y.description = 'Y-axis acceleration';
flight.channels.accel_y.sensor_id = 'ACC_001';
flight.channels.accel_y.location = 'Wing tip - starboard';

% Z-axis channel
flight.channels.accel_z.data = accel_z;
flight.channels.accel_z.sample_rate = fs;
flight.channels.accel_z.units = 'g';
flight.channels.accel_z.start_time = 0.0;
flight.channels.accel_z.description = 'Z-axis acceleration';
flight.channels.accel_z.sensor_id = 'ACC_001';
flight.channels.accel_z.location = 'Wing tip - starboard';

% Convert to HDF5
convert_to_hdf5('example2_triaxial.h5', flight);

fprintf('Created: example2_triaxial.h5\n\n');


%% Example 3: Multiple Flights in One File
% Useful for comparing multiple test runs

fprintf('=== Example 3: Multiple Flights ===\n');

% Flight 1: Low amplitude test
duration = 20;
fs = 2000;
t = (0:1/fs:duration-1/fs)';
signal1 = 0.1*sin(2*pi*60*t) + 0.02*randn(size(t));

flights{1}.flight_id = 'Flight_001_Low';
flights{1}.date = '2025-01-22';
flights{1}.description = 'Low amplitude vibration test';
flights{1}.channels.accel_z.data = signal1;
flights{1}.channels.accel_z.sample_rate = fs;
flights{1}.channels.accel_z.units = 'g';
flights{1}.channels.accel_z.start_time = 0.0;

% Flight 2: Medium amplitude test
signal2 = 0.5*sin(2*pi*60*t) + 0.05*randn(size(t));

flights{2}.flight_id = 'Flight_002_Medium';
flights{2}.date = '2025-01-22';
flights{2}.description = 'Medium amplitude vibration test';
flights{2}.channels.accel_z.data = signal2;
flights{2}.channels.accel_z.sample_rate = fs;
flights{2}.channels.accel_z.units = 'g';
flights{2}.channels.accel_z.start_time = 0.0;

% Flight 3: High amplitude test
signal3 = 1.0*sin(2*pi*60*t) + 0.1*randn(size(t));

flights{3}.flight_id = 'Flight_003_High';
flights{3}.date = '2025-01-22';
flights{3}.description = 'High amplitude vibration test';
flights{3}.channels.accel_z.data = signal3;
flights{3}.channels.accel_z.sample_rate = fs;
flights{3}.channels.accel_z.units = 'g';
flights{3}.channels.accel_z.start_time = 0.0;

% Convert to HDF5
convert_to_hdf5('example3_multiple_flights.h5', flights);

fprintf('Created: example3_multiple_flights.h5\n\n');


%% Example 4: High Sample Rate Data (Typical for Aerospace)
% Demonstrates handling of large datasets

fprintf('=== Example 4: High Sample Rate Data ===\n');

% Realistic aerospace parameters
duration = 100;   % 100 seconds
fs = 40000;       % 40 kHz sample rate (typical for high-frequency vibration)
t = (0:1/fs:duration-1/fs)';
n_samples = length(t);

fprintf('Generating %d samples (%.1f MB)...\n', n_samples, n_samples*8/(1024*1024));

% Generate broadband vibration with multiple frequency components
signal = zeros(n_samples, 1);
frequencies = [50, 120, 250, 500, 1000, 2000, 5000];  % Hz
amplitudes = [0.5, 0.3, 0.2, 0.15, 0.1, 0.05, 0.02];   % g

for i = 1:length(frequencies)
    signal = signal + amplitudes(i) * sin(2*pi*frequencies(i)*t);
end

% Add broadband noise
signal = signal + 0.01*randn(n_samples, 1);

% Package into flight structure
flight.flight_id = 'High_Rate_Test_001';
flight.date = '2025-01-22';
flight.description = 'High sample rate vibration test - 40 kHz';
flight.channels.accel_z.data = signal;
flight.channels.accel_z.sample_rate = fs;
flight.channels.accel_z.units = 'g';
flight.channels.accel_z.start_time = 0.0;
flight.channels.accel_z.description = 'Z-axis acceleration - broadband vibration';
flight.channels.accel_z.sensor_id = 'ACC_HF_001';
flight.channels.accel_z.location = 'Engine mount';

% Convert to HDF5
convert_to_hdf5('example4_high_rate.h5', flight);

fprintf('Created: example4_high_rate.h5\n\n');


%% Example 5: Converting Existing MATLAB Data
% Template for converting your actual data

fprintf('=== Example 5: Template for Your Data ===\n');

% UNCOMMENT AND MODIFY THIS SECTION FOR YOUR DATA:
%
% % Load your existing MATLAB data
% load('your_data_file.mat');  % Replace with your file
% 
% % Extract your data variables
% % Adjust variable names to match your data
% time_vector = your_time_data;
% accel_x_data = your_x_axis_data;
% accel_y_data = your_y_axis_data;
% accel_z_data = your_z_axis_data;
% sample_rate = your_sample_rate;
% 
% % Package into flight structure
% flight.flight_id = 'Your_Flight_ID';
% flight.date = 'YYYY-MM-DD';
% flight.description = 'Description of your test';
% 
% % X-axis
% flight.channels.accel_x.data = accel_x_data;
% flight.channels.accel_x.sample_rate = sample_rate;
% flight.channels.accel_x.units = 'g';  % or 'm/s^2', 'V', etc.
% flight.channels.accel_x.start_time = time_vector(1);
% flight.channels.accel_x.description = 'X-axis acceleration';
% 
% % Y-axis
% flight.channels.accel_y.data = accel_y_data;
% flight.channels.accel_y.sample_rate = sample_rate;
% flight.channels.accel_y.units = 'g';
% flight.channels.accel_y.start_time = time_vector(1);
% flight.channels.accel_y.description = 'Y-axis acceleration';
% 
% % Z-axis
% flight.channels.accel_z.data = accel_z_data;
% flight.channels.accel_z.sample_rate = sample_rate;
% flight.channels.accel_z.units = 'g';
% flight.channels.accel_z.start_time = time_vector(1);
% flight.channels.accel_z.description = 'Z-axis acceleration';
% 
% % Convert to HDF5
% convert_to_hdf5('your_output_file.h5', flight);

fprintf('See commented code in this section for template.\n\n');


%% Verify HDF5 Files
% Quick check that files were created

fprintf('=== Verification ===\n');
files = {'example1_simple.h5', 'example2_triaxial.h5', ...
         'example3_multiple_flights.h5', 'example4_high_rate.h5'};

for i = 1:length(files)
    if exist(files{i}, 'file')
        info = h5info(files{i});
        fprintf('✓ %s - %d flight(s)\n', files{i}, length(info.Groups));
    else
        fprintf('✗ %s - NOT FOUND\n', files{i});
    end
end

fprintf('\nAll example files created successfully!\n');
fprintf('You can now load these files in SpectralEdge.\n');
