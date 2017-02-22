# Description
This plugin exports pupillabs eye tracking gaze to Ivybus

# Prerequesities :
 * [pupil software installed](https://github.com/pupil-labs/pupil/wiki/Getting-Started)

# Installation
 * activate plugin `pupil_usybus_controller.py` [Refer Load your plugin automatically](https://github.com/pupil-labs/pupil/wiki/Plugin-Guide)

# Tests

    # Subscribes data published by plugin
    python ./eye_tracking_usybus_subscriber.py
    
Subscribed data can be exported to a file `gaze_from_ub.csv` and compared to exported file from pupil player running :    

    ./tests/test_gaze.sh ./Marker_Tracking_Demo_Recording/exports/0-3235/gaze_postions.csv ./gaze_from_ub.csv 10
    run test on 6 of gaze data
    TEST OK

# References
[Pupillabs](https://pupil-labs.com/)
[Ivybus](http://www.eei.cena.fr/products/ivy/)
[Pupil data format](https://github.com/pupil-labs/pupil/wiki/Data-Format#pupil-positions)
