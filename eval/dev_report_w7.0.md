# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| twin (31 parts) | 310 | 67 % | 93 % | 4.6 |
| all | 310 | 67 % | 93 % | 4.6 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 55 | 53 % |
| question | 0 | 0 % |
| stop | 39 | 38 % |
| reading | 9 | 9 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 1.0 |  |  |
| hotend_thermistor | 30 % | 100 % | 4.3 | stop | umbilical_wiring |
| nozzle | 80 % | 100 % | 5.2 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 4.6 | knowledge | hotend_fan |
| extruder_motor | 40 % | 100 % | 5.2 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 5.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 7.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 4.0 |  |  |
| xy_belts | 100 % | 100 % | 4.5 |  |  |
| xy_pulleys_idlers | 50 % | 100 % | 6.1 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.9 |  |  |
| y_linear_rails | 100 % | 100 % | 5.9 |  |  |
| toolhead | 50 % | 50 % | 7.4 | reading | xy_belts |
| z_motor_leadscrew | 80 % | 100 % | 7.0 | stop | z_rails |
| z_rails | 40 % | 80 % | 4.4 | knowledge | z_motor_leadscrew |
| z_endstop | 60 % | 60 % | 4.0 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 3.2 |  |  |
| bed_thermistor | 50 % | 100 % | 6.0 | knowledge | bed_plate_carrier |
| bed_plate_carrier | 100 % | 100 % | 4.0 |  |  |
| controller_board | 50 % | 50 % | 2.8 | knowledge | host_computer |
| umbilical_wiring | 40 % | 90 % | 4.8 | stop | hotend_thermistor |
| power_supply | 10 % | 100 % | 2.1 | stop | mains_power_input |
| host_computer | 90 % | 100 % | 6.6 | knowledge | hotend_thermistor |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 60 % | 100 % | 7.0 | knowledge | toolhead |
| slicer_settings | 50 % | 50 % | 5.5 | knowledge | nozzle |
| filament_material | 90 % | 90 % | 4.2 | knowledge | hotend_fan |
| mains_power_input | 100 % | 100 % | 2.0 |  |  |
| dc_power_wiring | 0 % | 100 % | 3.4 | knowledge | host_computer |
| bed_thermal_fuse | 100 % | 100 % | 2.0 |  |  |