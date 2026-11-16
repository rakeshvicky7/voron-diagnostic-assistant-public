# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| twin (31 parts) | 310 | 62 % | 91 % | 4.6 |
| all | 310 | 62 % | 91 % | 4.6 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 59 | 50 % |
| question | 0 | 0 % |
| stop | 49 | 42 % |
| reading | 10 | 8 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 40 % | 100 % | 6.5 | stop | umbilical_wiring |
| nozzle | 80 % | 100 % | 5.2 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 5.2 | knowledge | extruder_motor |
| extruder_motor | 40 % | 100 % | 4.8 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 6.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 4.8 |  |  |
| xy_belts | 50 % | 100 % | 5.5 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 40 % | 50 % | 5.8 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.6 |  |  |
| y_linear_rails | 100 % | 100 % | 5.6 |  |  |
| toolhead | 50 % | 50 % | 3.8 | reading | xy_belts |
| z_motor_leadscrew | 80 % | 100 % | 6.3 | stop | z_rails |
| z_rails | 40 % | 80 % | 4.4 | knowledge | z_motor_leadscrew |
| z_endstop | 60 % | 60 % | 4.0 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 3.2 |  |  |
| bed_thermistor | 50 % | 100 % | 5.5 | knowledge | bed_plate_carrier |
| bed_plate_carrier | 100 % | 100 % | 4.5 |  |  |
| controller_board | 50 % | 50 % | 2.5 | knowledge | host_computer |
| umbilical_wiring | 10 % | 90 % | 6.2 | stop | hotend_thermistor |
| power_supply | 10 % | 100 % | 2.2 | stop | mains_power_input |
| host_computer | 80 % | 100 % | 6.3 | knowledge | bed_heater |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 30 % | 100 % | 6.7 | knowledge | toolhead |
| slicer_settings | 50 % | 50 % | 5.5 | knowledge | nozzle |
| filament_material | 60 % | 90 % | 3.8 | knowledge | firmware_config_macros |
| mains_power_input | 100 % | 100 % | 2.0 |  |  |
| dc_power_wiring | 0 % | 100 % | 3.0 | knowledge | host_computer |
| bed_thermal_fuse | 100 % | 100 % | 2.0 |  |  |