# Give your professor a link to the assistant

The assistant keeps running on your laptop (full mode, with the language model). A free Cloudflare "quick tunnel" gives it a temporary web address that works from any computer.

## One-time setup
1. Open PowerShell and run: `winget install --id Cloudflare.cloudflared`
2. Close PowerShell.

## Each time you want to share it
1. Start the **Ollama** app.
2. Double-click **`start_demo_link.bat`** in the `agent` folder. Two windows open.
3. In the second window, find the line with an address like `https://some-words.trycloudflare.com`. Send that link to your professor.
4. Before sending, open the link yourself on your phone (mobile data, not your Wi-Fi) to check that it works.
5. When the demo is over, close both windows. The link stops working.

## Keep in mind
- Your laptop must stay **on, awake and online** the whole time. Set Windows sleep to "Never" while plugged in (Settings > System > Power).
- The link is **new each time** you start the file. Send the new one.
- Anyone who has the link can use the assistant while it runs, so share it only with your professor and close it afterwards.
- During the demo, confirmed cases are **not saved**, so visitors do not change what the assistant has learned.
- The first page load takes 10 to 30 seconds on his side (the 3D model is 23 MB).
- The language model runs on your laptop, so a refined answer can take up to a minute. The simulation starts after at most 8 seconds anyway.

## Suggested 10-minute demo
1. **Home** (`/`): the two parts of the product.
2. **Assembly**: press *Assemble*, then ask the guide "How are the belts connected to the motors?".
3. **Repair assistant**: type "The extruder clicks and the walls are thin with gaps". Show the ranked parts with checks and sources.
4. **Open simulation**: write "nozzle temperature 400" (refused, with the allowed range), then continue. Answer "Yes, the same", see the part glow, then "Yes, it is faulty" for the repair steps.
5. **Results**: 69 held-out cases, right part first 65 %, within two checks 91 % (`FINAL_MODEL.md`).
