# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| twin (31 parts) | 310 | 67 % | 85 % | 4.9 |
| all | 310 | 67 % | 85 % | 4.9 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 66 | 65 % |
| question | 0 | 0 % |
| stop | 23 | 23 % |
| reading | 13 | 13 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 40 % | 40 % | 6.3 | knowledge | bed_thermistor |
| nozzle | 80 % | 100 % | 4.9 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 4.8 | knowledge | extruder_motor |
| extruder_motor | 40 % | 100 % | 5.2 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 6.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 4.0 |  |  |
| xy_belts | 50 % | 50 % | 5.5 | knowledge | z_motor_leadscrew |
| xy_pulleys_idlers | 40 % | 50 % | 5.3 | knowledge | extruder_gears_guidler |
| x_linear_rail | 100 % | 100 % | 5.6 |  |  |
| y_linear_rails | 100 % | 100 % | 5.6 |  |  |
| toolhead | 10 % | 60 % | 7.5 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 70 % | 100 % | 6.4 | stop | z_rails |
| z_rails | 40 % | 80 % | 4.6 | knowledge | bed_plate_carrier |
| z_endstop | 60 % | 60 % | 3.0 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 3.2 |  |  |
| bed_thermistor | 100 % | 100 % | 6.0 |  |  |
| bed_plate_carrier | 100 % | 100 % | 4.0 |  |  |
| controller_board | 50 % | 100 % | 5.0 | knowledge | host_computer |
| umbilical_wiring | 50 % | 100 % | 4.8 | stop | hotend_thermistor |
| power_supply | 100 % | 100 % | 4.0 |  |  |
| host_computer | 100 % | 100 % | 5.3 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 0 % | 30 % | 6.4 | knowledge | bed_plate_carrier |
| slicer_settings | 0 % | 0 % | 5.3 | stop | nozzle |
| filament_material | 90 % | 90 % | 5.9 | knowledge | extruder_motor |
| mains_power_input | 70 % | 100 % | 3.3 | knowledge | power_supply |
| dc_power_wiring | 90 % | 90 % | 5.6 | knowledge | host_computer |
| bed_thermal_fuse | 100 % | 100 % | 2.0 |  |  |