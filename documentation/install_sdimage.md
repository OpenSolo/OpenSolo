## Manual SD Card Image Install ##
This procedure is for users that need to write a full image to the IMX companion computer SD card. This is usually to recover from some catastrophic disc corruption issue. But you can use this process to do the install from scratch if desired.

### WARNING ###
This requires extensive disassembly of the Solo and/or controller in order to access the SD cards. You will need to scrape the glue off the SD card slots to remove the cards. This process is not recommended unless you actually need to do it for some reason.

### SETUP ##
1. **Required Applications:** 
   - Download and install the [7zip application](http://www.7-zip.org/download.html) if you don't already have it. 7zip is the only format that could compress the image small enough for github release attachment. You'll need 7zip or other compatible application to unzip the SD Card image files you downloaded in step 1.
   - Download and install the [Win32 Disk Imager application](https://sourceforge.net/projects/win32diskimager/files/latest/download) if you don't already have it. This is the application that will burn the image to the SD Card.

2. **SD Card Image Files:** Download the `Open Solo SD Card Image.7z` file from the github release attachments. There is one for the copter and one for the controller, with the version in the file name (such as 3.0.0). Download either one or both, whichever you need. Unzip using 7zip somewhere convenient on your computer. The zip file contains an `img` file for the Controller or Copter SD cards.


### COPTER SD CARD ##
It is strongly suggested that you only remove one SD card at a time if you're planning to do both the copter and the controller. This is to avoid mixing the cards up since they appear identical.

1. Insert the SD card card from the copter's IMX companion computer into your PC's SD card slot.

2. Open the Win32 Disk Imager application

3. Under _device_, make sure it is set to the SD card's drive letter on your PC.

4. Under _Image File_, select open and navigate to and select the Open Solo _copter_ SD image file from the zip file.

5. Press the _Write Button_ to begin writing the SD card image.  The write can take 20-60 minutes depending on how fast your PC is.  Do not interrupt the write process!!

6. Place the completed SD card back into the copter's IMX companion computer. Power up and verify everything boots up as it should.  Presuming there is nothing else wrong, the IMX and Pixhawk should boot up normally.

### CONTROLLER SD CARD ##
It is strongly suggested that you only remove one SD card at a time if you're planning to do both the copter and the controller. This is to avoid mixing the cards up since they appear identical.

1. Insert the SD card card from the Controller's IMX companion computer into your PC's SD Card slot.

2. Open the Win32 Disk Imager application

3. Under _device_, make sure it is set to the SD card's drive letter on your PC.

4. Under _Image File_, select open and navigate to and select the Open Solo _controller_ SD image file from the zip file.

5. Press the _Write Button_ to begin writing the SD card image.  The write can take 20-60 minutes depending on how fast your PC is.  Do not interrupt the write process!!

6. Place the completed SD card back into the controller's IMX companion computer. Power up and verify everything boots up as it should.  Presuming there is nothing else wrong, the controller should boot up normally.


### Execution ###
From this point forward, it is the same as any other installation method.

1. **Factory reset the Solo and Controller:** Use the standard factory reset procedure on the Solo and Controller. However, if you only did the image for one, you only need to do the one. Since we just installed Open Solo on the recovery partitions, they are factory resetting to Open Solo! They will then automatically execute a second update procedure, cleanly installing Open Solo on the system partition.

    - **Copter:** _Start with the copter powered off_. Use a paper clip or similar poking apparatus to press and hold Solo’s Pair button while powering on Solo. Make sure you feel the Pair button click down underneath the paper clip to verify you have properly activated the button. Continue holding the Pair button for at least 15 seconds after power-up. Below the Accessory Port and adjacent to the Pair button is a small orange LED Pair indicator light. Once this light starts flashing rapidly, about five times per second, release the Pair button.
    - You will likely hear the Pixhawk reboot 2-3 times. This is normal.
    - **Controller:** _Start with the controller powered off_. Hold the Power and Fly buttons simultaneously until you see the controller-updating display.
    - You will likely see the controller reboot and say update success twice. This is also normal.
    - It is difficult to know exactly what stage it is at since it can't speak and isn't telepathic. The process takes about 6 minutes on both the solo and the controller.  So just wait about 6 minutes.

2. **Pair:** Hit the pair button under the Solo with a small pointy poking apparatus like a paper clip for 2 seconds to get the controller and solo re-paired. When the controller tells you it has detected the solo, hold the A and B button for 3 seconds... which is the second set of vibrations... until the the screen says pairing in progress. If the copter and controller are not pairing, reboot both. They may have timed out.

3. **Reconnect mobile device:** You will need to reconnect your mobile device to Solo's WiFi now.  Since it did a factory reset, the Solo and controller are using their default WiFi SSID and password (the default password is `sololink`).

4. **Load applicable parameter packages:** If you have a HERE GPS/Compass, and/or Ian's landing gear mod, you will need to change or load those parameter packages. You can load the parameter packages in Solex or SidePilot.  Or you can change them manually in Mission Planner or Tower.  If you're doing this procedure, it is assumed you know how to do this and don't need instructions on parameters.
   
### Installation Complete! ### 
Proceed to the [post-installation instructions!](../master/install_post.md)
