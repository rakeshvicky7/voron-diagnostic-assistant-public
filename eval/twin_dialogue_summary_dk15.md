# Dialogue test on the virtual printer (5 faults per part, 'I can't tell' rate 15%)

| Subset | Runs | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| all 31 parts | 155 | 34 % | 60 % | 5.2 |
| 28 evaluation parts | 140 | 34 % | 64 % | 5.4 |
| 3 extra power/bed parts | 15 | 27 % | 27 % | 3.5 |

| Part | Top-1 | Top-3 | Mean questions | Most frequent wrong answer |
|---|---|---|---|---|
| hotend_heater | 80 % | 100 % | 4.6 | hotend_thermistor |
| hotend_thermistor | 20 % | 40 % | 6.8 | bed_thermistor |
| nozzle | 20 % | 100 % | 3.2 | extruder_gears_guidler |
| heatbreak_ptfe | 20 % | 100 % | 4.6 | extruder_motor |
| extruder_motor | 20 % | 20 % | 5.6 | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | filament_material |
| hotend_fan | 0 % | 40 % | 4.4 | extruder_motor |
| part_cooling_fan | 0 % | 0 % | 7.6 | z_rails |
| xy_motors_drivers | 100 % | 100 % | 5.2 |  |
| xy_belts | 20 % | 40 % | 7.0 | slicer_settings |
| xy_pulleys_idlers | 20 % | 60 % | 6.4 | z_motor_leadscrew |
| x_linear_rail | 20 % | 40 % | 5.4 | xy_belts |
| y_linear_rails | 0 % | 40 % | 5.6 | xy_motors_drivers |
| toolhead | 0 % | 80 % | 5.6 | z_motor_leadscrew |
| z_motor_leadscrew | 20 % | 20 % | 5.8 | z_endstop |
| z_rails | 0 % | 20 % | 4.0 | bed_plate_carrier |
| z_endstop | 80 % | 100 % | 7.2 | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 5.0 |  |
| bed_thermistor | 20 % | 80 % | 6.6 | firmware_config_macros |
| bed_plate_carrier | 80 % | 100 % | 6.6 | z_motor_leadscrew |
| controller_board | 100 % | 100 % | 2.6 |  |
| umbilical_wiring | 20 % | 60 % | 4.6 | hotend_thermistor |
| power_supply | 60 % | 60 % | 6.8 | filament_runout_sensor |
| host_computer | 20 % | 100 % | 5.8 | bed_thermistor |
| filament_runout_sensor | 100 % | 100 % | 2.6 |  |
| firmware_config_macros | 20 % | 40 % | 6.6 | slicer_settings |
| slicer_settings | 0 % | 0 % | 5.0 | nozzle |
| filament_material | 20 % | 40 % | 4.4 | extruder_motor |
| mains_power_input | 80 % | 80 % | 3.0 | filament_runout_sensor |
| dc_power_wiring | 0 % | 0 % | 2.4 | host_computer |
| bed_thermal_fuse | 0 % | 0 % | 5.2 | bed_heater |