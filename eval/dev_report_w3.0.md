# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| twin (31 parts) | 310 | 66 % | 87 % | 4.7 |
| all | 310 | 66 % | 87 % | 4.7 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 54 | 51 % |
| question | 0 | 0 % |
| stop | 38 | 36 % |
| reading | 13 | 12 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 30 % | 100 % | 6.5 | stop | host_computer |
| nozzle | 80 % | 100 % | 4.7 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 5.4 | knowledge | extruder_motor |
| extruder_motor | 40 % | 100 % | 4.6 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 4.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 4.8 |  |  |
| xy_belts | 50 % | 50 % | 5.5 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 40 % | 50 % | 4.9 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.9 |  |  |
| y_linear_rails | 100 % | 100 % | 6.2 |  |  |
| toolhead | 50 % | 50 % | 5.9 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 80 % | 100 % | 6.9 | stop | z_rails |
| z_rails | 40 % | 80 % | 4.4 | knowledge | z_motor_leadscrew |
| z_endstop | 60 % | 60 % | 4.2 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 3.2 |  |  |
| bed_thermistor | 50 % | 100 % | 6.0 | stop | bed_plate_carrier |
| bed_plate_carrier | 100 % | 100 % | 4.5 |  |  |
| controller_board | 50 % | 50 % | 2.3 | knowledge | host_computer |
| umbilical_wiring | 50 % | 100 % | 4.7 | stop | hotend_thermistor |
| power_supply | 100 % | 100 % | 4.9 |  |  |
| host_computer | 100 % | 100 % | 5.3 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 0 % | 30 % | 6.5 | knowledge | bed_plate_carrier |
| slicer_settings | 50 % | 50 % | 5.5 | knowledge | nozzle |
| filament_material | 90 % | 90 % | 4.7 | knowledge | extruder_motor |
| mains_power_input | 90 % | 100 % | 3.5 | knowledge | power_supply |
| dc_power_wiring | 0 % | 100 % | 2.4 | knowledge | host_computer |
| bed_thermal_fuse | 100 % | 100 % | 2.0 |  |  |