# Put the assistant online permanently (Hugging Face Space, free, basic mode)

About 15 minutes. You do the sign-in steps yourself; the script does the rest.

## 1. Accounts
1. Create a free account on https://huggingface.co (if you do not have one).
2. A **private** Space can be opened only by you and by members of an organization that owns it. So that your professor can open it:
   - Create a free organization: https://huggingface.co/organizations/new (e.g. `rr-voron-thesis`).
   - Ask your professor to create a free Hugging Face account, then invite him: organization page > Settings > Members > Invite (role "read").
3. Create an access token: https://huggingface.co/settings/tokens > "Create new token" > type **Write** > copy it.
   Keep it secret: do not paste it in chats, screenshots or files.

## 2. Upload
In PowerShell, in the `agent` folder:
```
py -3.12 -m pip install -U huggingface_hub
py -3.12 deploy\upload_space.py rr-voron-thesis/voron-assistant
```
(Use your organization name before the `/`.) When asked, paste the token and press Enter.

The script creates the private Space, uploads about 25 MB (only what the online assistant needs; no evaluation data, training data or the third-party troubleshooting guide) and sets the Space description.

## 3. Wait and test
1. Open `https://huggingface.co/spaces/rr-voron-thesis/voron-assistant`. The status shows "Building" for 3 to 5 minutes, then "Running".
2. Test Home, Assembly (press Assemble) and Repair assistant (type a problem, open the simulation).
3. Send your professor the link. He signs in to Hugging Face to open it.

## Good to know
- **Basic mode only:** no language model online. Accuracy on the 69 held-out cases: 59 % right part first, 78 % within two checks (full mode on your laptop: 65 % and 91 %).
- **Sleeps after 48 hours without visitors.** The next visitor wakes it up; that takes about a minute.
- Visitors cannot change the saved case memory.
- **Update after code changes:** run the same upload command again.
- **Stop or delete:** Space page > Settings (pause or delete the Space).
- If the build fails, open the "Logs" tab on the Space page and send me the last lines.
