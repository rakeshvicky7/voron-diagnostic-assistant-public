"""Clarifying question for vague descriptions ("it makes noise", "it stopped", "prints are bad").

Used only when the symptom graph recognises no symptom in the first message. Instead of asking the user to write again,
the assistant names the broad topic it understood and offers the concrete symptoms of that topic as buttons.
Each button sends a sentence the symptom graph recognises (checked in the test at the bottom).
This does not change the diagnosis itself, so the evaluation results are not affected.
"""
import re

# topic: (words that point to it, short name, [(button label, sentence sent when clicked)])
TOPICS = [
 ("noise", r"\b(nois\w*|sound\w*|loud|rattl\w*|bang\w*|knock\w*|click\w*|grind\w*|squeak\w*|squeal\w*|buzz\w*|hum\w*|vibrat\w*|clunk\w*)\b", "a noise", [
   ("Grinding or scraping when the head moves", "grinding noise when the head moves"),
   ("Loud click or bang from the motors", "loud click from the motors"),
   ("Knock at every direction change", "knocking when the toolhead changes direction"),
   ("Squeaking when moving", "squeaking when moving"),
   ("The extruder clicks", "the extruder clicks"),
   ("A fan rattles or buzzes", "fan rattles"),
   ("Noise when the bed moves up or down", "z axis noise")]),
 ("stopped", r"\b(stop\w*|halt\w*|froze|freez\w*|died|dies|dead|shut\w*|turn(s|ed)? off|switch(es|ed)? off|pause\w*|abort\w*|quit\w*|crash(es|ed)?|in the middle)\b", "the printer stopping", [
   ("Everything went off (lights, fans)", "the whole printer switches off"),
   ("Screen says 'Lost communication with MCU'", "lost communication with mcu"),
   ("Head keeps moving, but no plastic comes out", "extrusion stops mid print"),
   ("It paused with a filament runout message", "filament runout"),
   ("A heater error (not heating at expected rate)", "heater extruder not heating at expected rate"),
   ("Klipper says 'ADC out of range'", "adc out of range"),
   ("The web page (Mainsail/Fluidd) froze", "web interface does not load")]),
 ("slow", r"\b(slow\w*|takes? (so |very |too )?long|sluggish)\b", "slow printing", [
   ("The hotend heats slowly", "hotend heats slowly"),
   ("The bed heats slowly", "bed heats slowly"),
   ("Thin walls or gaps when I print faster", "under extrusion only at high speed"),
   ("Layers shift when I print faster", "layer shift only at high speed")]),
 ("quality", r"\b(bad|ugly|poor\w*|quality|rough|messy|weird|wrong|fail\w*|not good|spaghetti|mess|defect\w*|looks? off)\b", "print quality", [
   ("Layers shift sideways", "layer shift"),
   ("Thin walls, gaps, weak parts", "under extrusion"),
   ("Blobs, too much plastic", "over extrusion"),
   ("Strings and oozing", "stringing"),
   ("First layer does not stick", "first layer not sticking"),
   ("Ripples after corners", "ringing"),
   ("Wavy lines up the walls", "z banding"),
   ("Corners lift off the bed", "corners lift")]),
 ("heat", r"\b(heat\w*|temp\w*|hot|cold|warm\w*|thermal|thermistor)\b", "temperature or heating", [
   ("The hotend does not heat (or heats slowly)", "hotend not heating"),
   ("The bed does not heat (or heats slowly)", "bed not heating"),
   ("The temperature jumps or spikes", "temperature spikes"),
   ("The temperature swings up and down", "temperature oscillates"),
   ("Klipper says 'ADC out of range'", "adc out of range")]),
 ("power", r"\b((not|won'?t|doesn'?t|does not|cannot|can'?t) (start|turn on|power|boot|connect)|no power|no lights?|nothing happens)\b", "starting up", [
   ("It does not turn on at all", "will not turn on"),
   ("The power supply LED is off", "psu led is off"),
   ("Klipper says 'Unable to connect'", "unable to connect"),
   ("Klipper shows a config error", "config error")]),
 ("extrusion", r"\b(filament|extru\w*|nozzle|clog\w*|jam\w*|plastic|under ?extru\w*)\b", "extrusion", [
   ("No plastic comes out at all", "no plastic comes out"),
   ("The extruder clicks", "the extruder clicks"),
   ("The filament gets chewed / ground", "filament ground down"),
   ("Extrusion stops after some minutes", "extrusion stops mid print"),
   ("Plastic leaks around the nozzle", "plastic leaking from the heater block")]),
 ("motion", r"\b(mov\w*|homing|home|axis|belt\w*|motor\w*|gantry|toolhead|bed)\b", "movement", [
   ("Layers shift sideways", "layer shift"),
   ("Homing stops early or bangs", "homing stops early"),
   ("The bed crashes when homing Z", "bed crashes when homing"),
   ("A belt climbs or rubs", "belt climbs"),
   ("The bed does not move up or down", "z does not move")]),
]
GENERAL = [("Layers shift sideways", "layer shift"), ("No plastic comes out", "no plastic comes out"),
           ("First layer does not stick", "first layer not sticking"), ("The whole printer switches off", "the whole printer switches off"),
           ("The hotend does not heat", "hotend not heating"), ("Grinding noise when moving", "grinding noise when the head moves"),
           ("An error message on the screen", "")]

SLOW_NOTE = ("If the whole print is simply slow but looks fine, that is usually the speed limits in printer.cfg "
             "(max_velocity, max_accel) or the slicer profile, not a broken part.")


def clarify(text, max_options=8):
    """Clarifying question and buttons for a description without a recognised symptom."""
    t = text.lower()
    hits = [(name, label, opts) for name, rx, label, opts in TOPICS if re.search(rx, t)]
    if not hits:
        return {"text": "I need a bit more detail to find the part. Which of these is closest to what you see? "
                        "Or describe it in other words (what you see, hear, or read on the screen).",
                "options": [{"label": l, "text": s} for l, s in GENERAL if s]}
    per = max(2, max_options // len(hits)); opts, seen = [], set()
    for _, _, o in hits:
        for l, s in o[:per]:
            if s not in seen: seen.add(s); opts.append({"label": l, "text": s})
    for _, _, o in hits:                       # fill up to max_options from the first topics
        for l, s in o:
            if len(opts) >= max_options: break
            if s not in seen: seen.add(s); opts.append({"label": l, "text": s})
    topics = " and ".join(label for _, label, _ in hits[:2])
    msg = f"I understood it is about {topics}, but I need a bit more detail to find the part. Which of these is closest?"
    if any(n == "slow" for n, _, _ in hits): msg += " " + SLOW_NOTE
    return {"text": msg + " You can also describe it in other words.", "options": opts[:max_options]}


if __name__ == "__main__":        # every button must lead to a recognised symptom
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.fmea.engine import link
    bad = [(l, s) for _, _, _, o in TOPICS for l, s in o if not link(s)] + [(l, s) for l, s in GENERAL if s and not link(s)]
    print("buttons without a recognised symptom:", bad or "none")
    for q in ["my printer is making lot of noise while working and the it is printing very slowly",
              "my printer stopped working in the middle of the print", "it is broken"]:
        r = clarify(q); print("\n" + q + "\n ", r["text"]); [print("   -", o["label"]) for o in r["options"]]
