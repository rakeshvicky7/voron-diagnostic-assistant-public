# Development yardstick (10 twin faults per part; 'can't tell' 15%; wrong answers 10%)

| Set | Cases | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| twin (31 parts) | 310 | 33 % | 62 % | 5.4 |
| all | 310 | 33 % | 62 % | 5.4 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 151 | 73 % |
| question | 0 | 0 % |
| stop | 46 | 22 % |
| reading | 11 | 5 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 70 % | 100 % | 5.8 | stop | hotend_thermistor |
| hotend_thermistor | 20 % | 40 % | 5.3 | knowledge | bed_thermistor |
| nozzle | 70 % | 90 % | 4.5 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 10 % | 70 % | 4.8 | stop | extruder_motor |
| extruder_motor | 20 % | 50 % | 4.9 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 70 % | 5.9 | stop | filament_material |
| hotend_fan | 0 % | 50 % | 4.1 | knowledge | extruder_motor |
| part_cooling_fan | 20 % | 20 % | 7.4 | knowledge | z_rails |
| xy_motors_drivers | 80 % | 90 % | 4.9 | stop | z_motor_leadscrew |
| xy_belts | 50 % | 50 % | 5.5 | knowledge | z_motor_leadscrew |
| xy_pulleys_idlers | 0 % | 50 % | 5.9 | knowledge | xy_motors_drivers |
| x_linear_rail | 10 % | 60 % | 5.5 | knowledge | xy_motors_drivers |
| y_linear_rails | 20 % | 80 % | 5.5 | knowledge | xy_motors_drivers |
| toolhead | 0 % | 20 % | 6.9 | knowledge | z_motor_leadscrew |
| z_motor_leadscrew | 70 % | 80 % | 6.9 | knowledge | z_rails |
| z_rails | 0 % | 50 % | 5.0 | knowledge | bed_plate_carrier |
| z_endstop | 50 % | 80 % | 6.0 | knowledge | bed_plate_carrier |
| bed_heater | 80 % | 90 % | 5.3 | stop | hotend_thermistor |
| bed_thermistor | 0 % | 30 % | 6.7 | knowledge | bed_plate_carrier |
| bed_plate_carrier | 70 % | 100 % | 5.6 | stop | z_motor_leadscrew |
| controller_board | 60 % | 100 % | 3.8 | knowledge | host_computer |
| umbilical_wiring | 20 % | 80 % | 4.7 | knowledge | hotend_thermistor |
| power_supply | 70 % | 80 % | 6.3 | stop | mains_power_input |
| host_computer | 30 % | 70 % | 6.9 | stop | bed_thermistor |
| filament_runout_sensor | 100 % | 100 % | 2.8 |  |  |
| firmware_config_macros | 20 % | 70 % | 6.6 | knowledge | part_cooling_fan |
| slicer_settings | 0 % | 0 % | 4.9 | knowledge | nozzle |
| filament_material | 30 % | 60 % | 6.7 | knowledge | slicer_settings |
| mains_power_input | 50 % | 80 % | 4.0 | knowledge | filament_runout_sensor |
| dc_power_wiring | 0 % | 10 % | 2.3 | knowledge | host_computer |
| bed_thermal_fuse | 0 % | 0 % | 5.2 | knowledge | bed_heater |