## Manual SSH Install ##

### WARNING ###
This procedure is for users that want to install Open Solo manually using various SSH and file transfer tools on a PC. If you are not familiar with SSH and copying files to/from the Solo, this procedure is not for you. This is for advanced users already familiar with the technology and procedures involved.


### SETUP ##
1. **Download** the `Open Solo x.x.x.zip` file from the release attachments and unzip somewhere convenient on your computer.

2. **Power up** the copter and controller. Both should be fully charged, paired, connected, and working normally.

3. **Connect** your PC to the Solo's WiFi.


### COPTER FILES ##

1. **SSH into the _Copter_** at address 10.1.1.10, password TjSDBkAu.

2. **Prepare for upload** by executing the following commands. When you execute the --get-image command, make sure it says "latest".
    ```
    sololink_config --update-prepare
    sololink_config --get-image   ## confirm "latest'
    umount /dev/mmcblk0p1
    mkfs.vfat /dev/mmcblk0p1 -n GOLDEN
    mkdir -p /tmp/golden
    mount /dev/mmcblk0p1 /tmp/golden
    ```
    
3. **Copy files** from inside the 3dr-solo.tar.gz file to the `/tmp/golden` directory on the Solo. _Not the tar file_. The individual files within it. You can copy it with SSH or use an app like WinSCP or FileZilla.
   - 3dr-solo-imx6solo-3dr-1080p.squashfs
   - imx6solo-3dr-1080p.dtb
   - u-boot.imx
   - uImage

4. **Verify the files copied. Refresh the folder in WinSCP or FileZilla... or run `ls /tmp/golden`. Make sure the files you see match the files you uploaded.

5. **Finalize the update** with the following final commands:
   ```
   umount /dev/mmcblk0p1
   touch /log/updates/FACTORYRESET
   ```

6. **Exit** the SSH session and exit any other apps (WinSCP/FileZilla).


### CONTROLLER FILES ##

1. **SSH into the _Controller_** at address 10.1.1.1, password TjSDBkAu.

5. **Prepare for upload** by executing the following commands. When you execute the --get-image command, make sure it says "latest".
    ```
    sololink_config --update-prepare
    sololink_config --get-image
    umount /dev/mmcblk0p1
    mkfs.vfat /dev/mmcblk0p1 -n GOLDEN
    mkdir -p /tmp/golden
    mount /dev/mmcblk0p1 /tmp/golden
    ```
    
6. **Copy files** from inside the _3dr-controller.tar.gz_ file to the `/tmp/golden` directory on the Controller. _Not the tar file_. The individual files within it. You can copy it with SSH or use an app like WinSCP or FileZilla.
   - 3dr-controller-imx6solo-3dr-artoo.squashfs
   - imx6solo-3dr-artoo.dtb
   - u-boot.imx
   - uImage

7. **Verify the files copied. Refresh the folder in WinSCP or FileZilla... or run `ls /tmp/golden`. Make sure the files you see match the files you uploaded.

8. **Finalize the update** with the following final commands:
   ```
   umount /dev/mmcblk0p1
   touch /log/updates/FACTORYRESET
   ```

9. **Exit** the SSH session and exit any other apps (WinSCP/FileZilla).

### Execution ###
From this point forward, it is the same as any other installation method.

4. **Reboot:** Power cycle the Solo and controller once the Copter and Controller steps above are complete. When they power back on, they will automatically begin a factory reset procedure. Since we just installed Open Solo on the recovery partitions, they are factory resetting to Open Solo! They will then automatically execute a second update procedure, cleanly installing Open Solo on the system partition.
    - You will likely hear the Pixhawk reboot tones 2-3 times.  This is normal.
    - You will likely see the controller reboot and say update success twice. This is also normal.
    - It is difficult to know exactly what stage it is at since it can't speak and isn't telepathic. The process takes about 6 minutes on both the solo and the controller. So just wait about 6 minutes.

5. **Pair:** Hit the pair button under the Solo with a small pointy poking apparatus like a paper clip for 2 seconds to get the controller and solo re-paired. When the controller tells you it has detected the solo, hold the A and B button for 3 seconds... which is the second set of vibrations... until the the screen says pairing in progress. If the copter and controller are not pairing, reboot both. They may have timed out.

6. **Reconnect mobile device:** You will need to reconnect your mobile device to Solo's WiFi now.  Since it did a factory reset, the Solo and controller are using their default WiFi SSID and password (the default password is `sololink`).

7. **Load applicable parameter packages:** If you have a HERE GPS/Compass, and/or Ian's landing gear mod, you will need to change or load those parameter packages. You can load the parameter packages in Solex or SidePilot.  Or you can change them manually in Mission Planner or Tower.  If you're doing this procedure, it is assumed you know how to do this and don't need instructions on parameters.
   
### Installation Complete! ### 
Proceed to the [post-installation instructions!](../master/install_post.md)
