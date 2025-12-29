
# Setting up Lip-Sync for VTube Studio

To make your avatar's mouth move when Karien speaks, you need to route Karien's audio output (which plays through your system speakers) into VTube Studio's microphone input.

Since macOS doesn't natively allow application audio to be used as microphone input, we use a virtual audio driver.

## Step 1: Install BlackHole
**BlackHole** is a free, open-source virtual audio driver for macOS.

1.  **Install via Homebrew** (recommended):
    ```bash
    brew install blackhole-2ch
    ```
    *Alternatively, download installer from [existential.audio/blackhole](https://existential.audio/blackhole/)*

## Step 2: Create a Multi-Output Device
You want to hear Karien **AND** have VTube Studio "hear" her. To do this, we output audio to both your headphones/speakers and BlackHole.

1.  Open **Audio MIDI Setup** (cmd+space, type "Audio MIDI Setup").
2.  Click the **+** (plus) icon in the bottom left corner.
3.  Select **Create Multi-Output Device**.
4.  In the right panel, check the boxes for:
    *   **BlackHole 2ch**
    *   **Your Headphones / External Speakers** (device you want to listen on)
5.  (Optional) Rename "Multi-Output Device" to something like "Karien Audio".
6.  **Right-click** on this new device in the left sidebar and select **"Use This Device For Sound Output"**.

**Note:** When using a Multi-Output device, macOS volume controls might be disabled. You may need to control volume on your physical speakers/headphones.


## Step 3: Configure VTube Studio
### 3.1 Enable Microphone Input
1.  Open **VTube Studio**.
2.  Go to **Settings** (Double-click screen -> Gear icon).
3.  Click the **Lipsync** tab (Microphone icon on the top bar).
4.  Under **Microphone**, enable "Use Microphone".
5.  Select **BlackHole 2ch** from the device list.
6.  Wait a moment. Speak or play audio; you should see the "Volume" bar move.
7.  Adjust the **Volume Gain** slider in this menu if the movement is too small.

### 3.2 Link Audio to Mouth Movement
Now we need to tell the model to use this volume to open its mouth.

1.  Click the **Model Settings** tab (Person/Avatar icon on the top bar).
2.  Select the **Parameters** sub-tab (3rd icon, looks like a list with sliders).
3.  Scroll down to find the parameter named **Mouth Open** (ParamMouthOpen).
4.  Click on it to expand settings.
5.  Find the **Input** setting (it might say "MouthOpen" or "VoiceVolume").
6.  Change the **Input** to **VoiceVolumePlusMouthOpen**. 
    *   *This combines camera tracking with audio volume.*
7.  Ensure the "Output" is set to the standard Mouth Open parameter.


## Step 4: Test
1.  Run Karien (`python main.py`).
2.  Make her speak.
3.  Your avatar should now lip-sync to her voice!
