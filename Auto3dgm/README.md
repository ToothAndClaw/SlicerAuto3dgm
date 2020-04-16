# How to install the extension
-----------

# The below is outdated. See the workshop instructions:

https://github.com/SlicerMorph/S_2019/tree/master/Lab09_Auto3dgm


### Download and install 3d Slicer

https://download.slicer.org/


NB: Make sure to install version 4.11 or newer (preview version as of Dec 14 2019)


-----------

### Install scipy and lap manually:

1) Open Slicer and paste the following to the python interactor:


        from pip._internal import main
        main(['install','scipy'])
        main(['install','lap'])

NB: Different operating systems may need different commands.

2) Close 3d Slicer.

### Downloading and Setting up the extension

1) Open terminal, `cd` to the Slicer installation directory
2) Dowload the extension:

        git clone --recursive https://github.com/ToothAndClaw/auto3dgmSlicerExtension



3) Open 3d Slicer, select Extension Wizard

4) Choose the folder auto3dgmSlicerExtension/Auto3dgm




