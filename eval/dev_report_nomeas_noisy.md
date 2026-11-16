# Development yardstick (6 twin faults per part; 'can't tell' 40%; wrong answers 10%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 186 | 48 % | 79 % | 6.0 | 66 % | 6.0 |
| all | 186 | 48 % | 79 % | 6.0 | 66 % | 6.0 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 27 | 28 % |
| question | 0 | 0 % |
| stop | 57 | 59 % |
| reading | 12 | 12 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 3.2 |  |  |
| hotend_thermistor | 50 % | 83 % | 7.7 | stop | firmware_config_macros |
| nozzle | 50 % | 67 % | 5.8 | stop | extruder_motor |
| heatbreak_ptfe | 0 % | 100 % | 5.5 | knowledge | extruder_motor |
| extruder_motor | 50 % | 100 % | 5.7 | stop | filament_material |
| extruder_gears_guidler | 67 % | 67 % | 6.5 | stop | firmware_config_macros |
| hotend_fan | 17 % | 83 % | 4.7 | stop | extruder_motor |
| part_cooling_fan | 67 % | 83 % | 6.5 | stop | slicer_settings |
| xy_motors_drivers | 100 % | 100 % | 6.3 |  |  |
| xy_belts | 83 % | 100 % | 6.3 | stop | xy_motors_drivers |
| xy_pulleys_idlers | 17 % | 83 % | 5.8 | stop | xy_motors_drivers |
| x_linear_rail | 17 % | 50 % | 6.5 | stop | xy_belts |
| y_linear_rails | 17 % | 50 % | 6.5 | stop | xy_belts |
| toolhead | 33 % | 50 % | 7.5 | reading | xy_belts |
| z_motor_leadscrew | 67 % | 100 % | 6.5 | stop | z_rails |
| z_rails | 67 % | 67 % | 6.5 | knowledge | bed_plate_carrier |
| z_endstop | 67 % | 83 % | 6.2 | knowledge | bed_plate_carrier |
| bed_heater | 50 % | 67 % | 6.0 | stop | filament_material |
| bed_thermistor | 50 % | 83 % | 7.0 | stop | filament_material |
| bed_plate_carrier | 83 % | 100 % | 6.0 | stop | z_motor_leadscrew |
| controller_board | 50 % | 67 % | 5.8 | knowledge | power_supply |
| umbilical_wiring | 0 % | 33 % | 7.0 | stop | firmware_config_macros |
| power_supply | 17 % | 100 % | 5.7 | stop | mains_power_input |
| host_computer | 33 % | 83 % | 7.8 | stop | power_supply |
| filament_runout_sensor | 100 % | 100 % | 3.3 |  |  |
| firmware_config_macros | 17 % | 67 % | 6.8 | knowledge | toolhead |
| slicer_settings | 0 % | 17 % | 5.8 | stop | extruder_motor |
| filament_material | 33 % | 67 % | 5.7 | knowledge | extruder_gears_guidler |
| mains_power_input | 100 % | 100 % | 5.5 |  |  |
| dc_power_wiring | 33 % | 100 % | 4.8 | stop | host_computer |
| bed_thermal_fuse | 67 % | 100 % | 5.0 | stop | bed_heater |