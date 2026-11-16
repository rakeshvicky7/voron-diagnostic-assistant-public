# Virtual printer: validation

Design values used: 38, of which 25 come from the documents and 13 are general engineering values (GEN).

## 1. Healthy printer (30 runs)

All answers normal and all engineering checks pass.

## 2-4. Each part with a fault (40 runs, random severity 0.2-0.95)

| Part | Fault modes (runs) | Technician notices a problem | Cards agree | Engineering check names it | Most frequent abnormal answers |
|---|---|---|---|---|---|
| hotend_heater | - (40) | 100 % | 75 % | 100 % | board_seen=Yes, it is listed; which_temp=The hotend; stop_type=Klipper shows an error and shuts down |
| hotend_thermistor | - (40) | 100 % | 69 % | 100 % | board_seen=Yes, it is listed; which_temp=The hotend; stop_type=Klipper shows an error and shuts down |
| nozzle | heavy clog (20); full clog (4); partial clog (16) | 100 % | 100 % | 60 % | motor_behaviour=Clicks / jumps back; flow_state=Less than normal / gaps in lines; flow_state=Nothing at all |
| heatbreak_ptfe | gap between PTFE and nozzle: plug forms (32); gap between PTFE and nozzle: leak (8) | 100 % | 100 % | 0 % | motor_behaviour=Clicks / jumps back; flow_state=Starts fine, then stops mid-print; flow_state=Leaks around the nozzle |
| extruder_motor | weak motor / low current (30); open coil (10) | 100 % | 100 % | 25 % | motor_behaviour=Clicks / jumps back; flow_state=Less than normal / gaps in lines; flow_state=Nothing at all |
| extruder_gears_guidler | guidler too loose (20); worn or slipping drive gear (20) | 82 % | 100 % | 0 % | motor_behaviour=Gears turn but filament does not move; flow_state=Less than normal / gaps in lines |
| hotend_fan | - (40) | 100 % | 100 % | 0 % | motor_behaviour=Clicks / jumps back; flow_state=Starts fine, then stops mid-print |
| part_cooling_fan | - (40) | 100 % | 100 % | 0 % | part_fan_state=No, it does not spin; surface=Drooping overhangs, curled corners |
| xy_motors_drivers | driver overheats, current drops (40) | 100 % | 100 % | 100 % | shift_axis=Diagonal / both; noise=Clicking or thumping |
| xy_belts | belts loose (24); belts unequal (16) | 100 % | 100 % | 100 % | surface=Ringing / ghosting (ripples after corners); shift_axis=Diagonal / both; noise=Clicking or thumping |
| xy_pulleys_idlers | loose pulley grub screw (20); worn idler bearing (20) | 100 % | 100 % | 20 % | shift_axis=Diagonal / both; noise=Grinding / scraping; move_by_hand=Rough in both |
| x_linear_rail | dry or damaged X rail (40) | 100 % | 100 % | 0 % | move_by_hand=Rough or tight in X; noise=Clicking or thumping; shift_axis=X only |
| y_linear_rails | dry or damaged Y rails (40) | 100 % | 100 % | 0 % | move_by_hand=Rough or tight in Y; shift_axis=Y only; noise=Clicking or thumping |
| toolhead | loose toolhead parts (40) | 100 % | 71 % | 0 % | surface=Ringing / ghosting (ripples after corners); noise=Clicking or thumping; first_layer=Changes from print to print |
| z_motor_leadscrew | binding lead screw / nut (30); motor or coupler failed (10) | 88 % | 68 % | 88 % | surface=Wavy or uneven layer lines (Z banding); z_home=Stops too early; first_layer=Changes from print to print |
| z_rails | binding Z rails (40) | 82 % | 90 % | 0 % | surface=Wavy or uneven layer lines (Z banding); first_layer=Changes from print to print; z_home=Stops too early |
| z_endstop | switch mount loose (16); switch does not actuate (6); broken wire (NC reads triggered) (18) | 88 % | 71 % | 0 % | board_seen=Yes, it is listed; stop_type=Klipper shows an error and shuts down; z_home=Stops too early |
| bed_heater | - (40) | 100 % | 87 % | 100 % | fuse_state=About 0 ohm (closed); first_layer=Too high / not sticking everywhere; board_seen=Yes, it is listed |
| bed_thermistor | - (40) | 100 % | 82 % | 0 % | fuse_state=About 0 ohm (closed); board_seen=Yes, it is listed; which_temp=The bed |
| bed_plate_carrier | plate loose / warped (18); bed not level (screws) (22) | 100 % | 95 % | 0 % | first_layer=Good on one side, bad on the other; first_layer=Changes from print to print; first_layer=Too squished everywhere |
| controller_board | - (40) | 100 % | 84 % | 62 % | stop_type=The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error); mcu_state='MCU unable to connect' at start; board_seen=No, it is missing |
| umbilical_wiring | broken strands in the toolhead cable (40) | 100 % | 76 % | 88 % | stop_type=Klipper shows an error and shuts down; wiggle=Yes, it appears or gets worse; which_temp=The hotend |
| power_supply | - (40) | 100 % | 84 % | 100 % | stop_type=Everything goes off: lights, fans, Raspberry Pi; restart=Comes back on by itself after a moment; board_seen=Yes, it is listed |
| host_computer | - (40) | 100 % | 100 % | 0 % | board_seen=Yes, it is listed; stop_type=Klipper shows an error and shuts down; mcu_state=The web page itself does not load |
| filament_runout_sensor | false runout triggers (40) | 100 % | 50 % | 0 % | board_seen=Yes, it is listed; stop_type=The print just pauses |
| firmware_config_macros | wrong Z position_endstop (12); wrong extruder rotation_distance (22); badly tuned PID (6) | 100 % | 100 % | 45 % | first_layer=Too squished everywhere; surface=Blobs, too much plastic; flow_state=Less than normal / gaps in lines |
| slicer_settings | speed / flow too high (22); nozzle temperature too low (18) | 100 % | 100 % | 55 % | motor_behaviour=Clicks / jumps back; flow_state=Less than normal / gaps in lines; flow_state=Nothing at all |
| filament_material | tangled spool (15); wet filament (19); thin / out-of-tolerance filament (6) | 100 % | 69 % | 0 % | surface=Stringing, rough or bubbly surface; motor_behaviour=Clicks / jumps back; flow_state=Starts fine, then stops mid-print |
| mains_power_input | - (40) | 100 % | 66 % | 5 % | stop_type=Everything goes off: lights, fans, Raspberry Pi; restart=Comes back on by itself after a moment; board_seen=Yes, it is listed |
| dc_power_wiring | - (40) | 100 % | 100 % | 2 % | board_seen=Yes, it is listed; mcu_state=Disconnects / 'Lost communication' during prints; stop_type=The Pi stays on, but motors and heaters stop ('Lost communication' / MCU error) |
| bed_thermal_fuse | - (40) | 100 % | 75 % | 100 % | board_seen=Yes, it is listed; fuse_state=Open (OL); which_temp=The bed |

Mean detectability: 98 %. Mean agreement with the cards: 87 % (over parts with abnormal answers).

## Disagreements between the twin and the cards (most frequent)

The twin gives this answer for this faulty part, but the cards do not list the part for the answer.

| Faulty part | Answer | Runs |
|---|---|---|
| hotend_heater | board_seen = Yes, it is listed | 40 |
| umbilical_wiring | board_seen = Yes, it is listed | 40 |
| filament_runout_sensor | board_seen = Yes, it is listed | 40 |
| mains_power_input | board_seen = Yes, it is listed | 40 |
| bed_thermal_fuse | board_seen = Yes, it is listed | 40 |
| hotend_thermistor | board_seen = Yes, it is listed | 26 |
| z_endstop | board_seen = Yes, it is listed | 24 |
| toolhead | noise = Clicking or thumping | 22 |
| bed_thermistor | board_seen = Yes, it is listed | 22 |
| controller_board | board_seen = Yes, it is listed | 19 |
| z_motor_leadscrew | z_home = Stops too early | 16 |
| umbilical_wiring | temp_behaviour = Rises slowly / never reaches target | 16 |
| filament_material | motor_behaviour = Clicks / jumps back | 15 |
| bed_heater | board_seen = Yes, it is listed | 14 |
| power_supply | first_layer = Too high / not sticking everywhere | 12 |
| z_motor_leadscrew | first_layer = Too high / not sticking everywhere | 10 |
| mains_power_input | motor_behaviour = Clicks / jumps back | 10 |
| mains_power_input | flow_state = Nothing at all | 9 |
| power_supply | fuse_state = About 0 ohm (closed) | 8 |
| z_rails | first_layer = Too high / not sticking everywhere | 5 |
| filament_material | board_seen = Yes, it is listed | 5 |
| power_supply | flow_state = Nothing at all | 4 |
| power_supply | motor_behaviour = Clicks / jumps back | 4 |
| hotend_thermistor | temp_behaviour = Rises slowly / never reaches target | 3 |
| bed_plate_carrier | first_layer = Too squished everywhere | 2 |