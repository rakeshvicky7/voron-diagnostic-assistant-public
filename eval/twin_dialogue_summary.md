# Dialogue test on the virtual printer (5 faults per part, 'I can't tell' rate 0%)

| Subset | Runs | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| all 31 parts | 155 | 35 % | 60 % | 5.1 |
| 28 evaluation parts | 140 | 36 % | 64 % | 5.3 |
| 3 extra power/bed parts | 15 | 27 % | 27 % | 3.2 |

| Part | Top-1 | Top-3 | Mean questions | Most frequent wrong answer |
|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 4.0 |  |
| hotend_thermistor | 0 % | 20 % | 6.2 | bed_thermistor |
| nozzle | 40 % | 100 % | 3.2 | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 4.0 | extruder_motor |
| extruder_motor | 20 % | 20 % | 4.8 | nozzle |
| extruder_gears_guidler | 0 % | 80 % | 6.4 | filament_material |
| hotend_fan | 0 % | 0 % | 4.0 | extruder_motor |
| part_cooling_fan | 0 % | 0 % | 8.0 | z_rails |
| xy_motors_drivers | 100 % | 100 % | 4.0 |  |
| xy_belts | 40 % | 40 % | 6.0 | slicer_settings |
| xy_pulleys_idlers | 40 % | 60 % | 6.6 | z_motor_leadscrew |
| x_linear_rail | 20 % | 100 % | 6.2 | xy_motors_drivers |
| y_linear_rails | 20 % | 100 % | 5.6 | xy_motors_drivers |
| toolhead | 0 % | 80 % | 6.4 | z_motor_leadscrew |
| z_motor_leadscrew | 20 % | 20 % | 5.8 | z_endstop |
| z_rails | 0 % | 0 % | 3.6 | bed_plate_carrier |
| z_endstop | 80 % | 80 % | 7.0 | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 4.2 |  |
| bed_thermistor | 0 % | 80 % | 6.8 | hotend_thermistor |
| bed_plate_carrier | 100 % | 100 % | 6.2 |  |
| controller_board | 100 % | 100 % | 2.6 |  |
| umbilical_wiring | 20 % | 100 % | 4.8 | hotend_thermistor |
| power_supply | 80 % | 80 % | 7.0 | filament_runout_sensor |
| host_computer | 20 % | 60 % | 6.2 | bed_thermistor |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |
| firmware_config_macros | 20 % | 40 % | 6.6 | extruder_gears_guidler |
| slicer_settings | 0 % | 0 % | 4.6 | nozzle |
| filament_material | 0 % | 20 % | 4.8 | extruder_motor |
| mains_power_input | 80 % | 80 % | 3.0 | filament_runout_sensor |
| dc_power_wiring | 0 % | 0 % | 1.6 | host_computer |
| bed_thermal_fuse | 0 % | 0 % | 5.0 | bed_heater |