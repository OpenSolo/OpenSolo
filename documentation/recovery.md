## Problem Recovery ##
If your installation has botched, you may have corrupted or failed to install the files onto the recovery parition of the IMX SD card. If that has happened, the IMX has nothing to boot with during the reset and you will be stuck.  This can be fixed manually by removing the SD card, copying the files onto it, and putting it back in the solo (or controller).

1. Open up the Solo or controller (whichever is busted).
2. Scrape the white glue off the SD card slot
3. Remove the SD card (it pushs in to lock/unlock like a normal SD card
   (yes, it is a pain.)
4. Put the SD card in your PC. It should appear as device called GOLDEN.


**You should see 4 files on the SD Card** looking at it on your PC. If these are missing or messed up, you've found the problem.
   - 3dr-solo-imx6solo-3dr-1080p.squashfs
   - imx6solo-3dr-1080p.dtb
   - u-boot.imx
   - uImage
   ![SD Files](https://github.com/OpenSolo/documentation/blob/master/sd_card_files.JPG? "SD card images")

To manually fix this problem, you need to grab the `3dr-solo.tar.gz` or `3dr-controller.tar.gz` file (whichever you're working on) from the bottom of the latest release notes (https://github.com/OpenSolo/documentation/releases).
1. Download the applicable file and unzip it.
2. Place the 4 files from the zip onto the SD card so it looks like the screen shot above.
3. Put the SD card back in the Solo. You may wish to put a dab of hot glue on it.
4. Power up the Solo.
5. It will most likely pick up where it left off executing a reset, basically step 4 of the Solex install instructions. Continue from there.
