# Description
This plugin exports pupillabs eye tracking gaze to Ivybus

# Prerequesities :
 * [pupil software installed](https://github.com/pupil-labs/pupil/wiki/Getting-Started)
 * python packages :
   * configparser
   * ivy-python

# Installation
 * activate plugin `pupil_usybus_controller.py` [Refer Load your plugin automatically](https://github.com/pupil-labs/pupil/wiki/Plugin-Guide)
 * if pupil installed from bundle (ubuntu, mac) : [refer this solution to include your system python packages](https://github.com/pupil-labs/pupil/issues/646) 

# pupil capture / player configuration
## pupil capture
"Detection & mapping mode" must be set to 2D

# Tests

    # Subscribes data published by plugin
    python ./eye_tracking_usybus_subscriber.py

# References
* [Pupillabs](https://pupil-labs.com/)
* [Ivybus](http://www.eei.cena.fr/products/ivy/)
* [Pupil data format](https://github.com/pupil-labs/pupil/wiki/Data-Format#pupil-positions)
* [some UI examples](https://github.com/pupil-labs/pyglui/blob/e4d260cf6e19c07b57d961619daa451ccc7f9837/example/example.py)
    
## Issues    
* [surface update in capture](https://github.com/pupil-labs/pupil/issues/683)
* [surface event in player](https://github.com/pupil-labs/pupil/issues/684) 
