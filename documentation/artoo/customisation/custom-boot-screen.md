# Creating a custom boot/shutdown screen
> You need to be comfortable with recompiling the artoo firmware before you can customise your controller.  You should see the [how to build artoo firmware](https://github.com/OpenSolo/documentation/blob/master/artoo/build-artoo-firmware.md) document and come back when you have an image that you built, successfully flashed onto artoo.

### Requirements
* Basic linux knowledge (sorry osx/windows users)
* GIMP (these instructions use gimp, anything capable of working with a colour indexed image should work)
* Ability to flash custom firmware onto artoo

### Some Handy Numbers
* Artoo max screen resolution: 320x240 pixels (4:3 aspect ratio)
* Any image's max colors: 256*
* *MUST be indexed

### Let's Start
#### Find your image
First find your new logo image. Images that are simple cartoons or logo's work best. Avoid gradients and complex colours as it will not look great. The typical nyan cat image is about as creative as you can get without looking terrible. Try to find pictures as close to a 4:3 aspect ratio as you can.

You can download the nyan cat sample image [here](https://github.com/OpenSolo/documentation/raw/master/artoo/customisation/sample-pics/nyan-cat-large.jpg).

#### Change image mode to "Indexed"
We need to decrease the "colour palette" to make the file size much smaller.

1) Click on `Image` > `Mode` > `Indexed...`. In the window that pops up select `Generate optimum palette`. Make sure the `Maximum number of colours: ` option is less than 255.

2) Click the `Convert` button. Now go to `File` > `Export As` and save it as something like `image-converted.jpg`.

#### Crop/Downsize
Open the image in GIMP. The first thing you should do is crop the image so that it fits a 4:3 aspect ratio. It also needs to be downsized so it's less than or equal to 320x240 pixels. To do this:

1) Go to `Image` > `Scale Image`. If it's a wide (horizontal) image type `240` pixels in the height column or if it's a narrow (vertical) image type `320` pixels into the width. The goal is to make the smallest dimension the same as artoo's maximum. (so we can crop off excess)

2) Click the `Scale` button to scale it. Now click on `Image` > `Canvas Size`. Make sure the chain link is un linked so that the aspect ratio is unconstrained. Now change the width to `320` and height to `240`. If you did step 1 correctly you should only need to change one.

3) In the image preview on the same window, drag the image sideways or up/down to crop it as you like. Click the `resize` button to confirm.

#### Recompile artoo firmware
Now we need to recompile artoo's firmware to include the new image.

1) Copy the newly created image to the `artoo/resources/images` directory of the artoo source code.

2) Edit the `artoo/resources/assets.cfg` file with your new image file name. The line you're looking for is called `Icon_Solo_Startup_Logo: ...`.  I highly suggest commenting out the old file and leaving it there.  Add a new line below so it looks like the following:
```
# Original Logo
#Icon_Solo_Startup_Logo: images/logo_startup/Solo_Logo.png
# My custom logo :)
Icon_Solo_Startup_Logo: images/logo_startup/nyan.png
```
3) Recompile and flash it!
