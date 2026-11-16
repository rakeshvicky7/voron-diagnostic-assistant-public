# Development yardstick (2 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 62 | 63 % | 84 % | 5.3 | 81 % | 5.4 |
| all | 62 | 63 % | 84 % | 5.3 | 81 % | 5.4 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 10 | 43 % |
| question | 0 | 0 % |
| stop | 10 | 43 % |
| reading | 3 | 13 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 50 % | 100 % | 7.0 | stop | hotend_heater |
| nozzle | 50 % | 100 % | 5.5 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 50 % | 100 % | 5.5 | reading | nozzle |
| extruder_motor | 0 % | 0 % | 6.0 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 4.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 6.0 |  |  |
| xy_belts | 50 % | 100 % | 6.0 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 50 % | 50 % | 5.5 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 6.5 |  |  |
| y_linear_rails | 100 % | 100 % | 6.5 |  |  |
| toolhead | 50 % | 50 % | 6.0 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 50 % | 100 % | 5.0 | stop | z_rails |
| z_rails | 50 % | 100 % | 4.5 | knowledge | bed_plate_carrier |
| z_endstop | 50 % | 50 % | 4.5 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 5.0 |  |  |
| bed_thermistor | 50 % | 100 % | 7.0 | stop | filament_material |
| bed_plate_carrier | 100 % | 100 % | 4.0 |  |  |
| controller_board | 50 % | 50 % | 5.0 | knowledge | host_computer |
| umbilical_wiring | 0 % | 0 % | 7.0 | stop | hotend_heater |
| power_supply | 100 % | 100 % | 4.5 |  |  |
| host_computer | 100 % | 100 % | 7.5 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 0 % | 50 % | 5.5 | knowledge | hotend_heater |
| slicer_settings | 50 % | 100 % | 6.0 | stop | nozzle |
| filament_material | 50 % | 50 % | 4.0 | knowledge | heatbreak_ptfe |
| mains_power_input | 100 % | 100 % | 3.0 |  |  |
| dc_power_wiring | 100 % | 100 % | 6.0 |  |  |
| bed_thermal_fuse | 0 % | 100 % | 6.0 | knowledge | hotend_thermistor |