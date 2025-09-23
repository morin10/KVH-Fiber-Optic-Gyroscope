# KVH-Fiber-Optic-Gyroscope
DSP-1760 &amp; DSP-3000 Fiber Optic Gyroscope ROS Package

## Edit UDEV Rules
```
$ cd /etc/udev/rules.d
$ touch dsp3000.rules
```

[dsp3000.rules]
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A1056P1I", SYMLINK+="dsp3000", MODE="0666", GROUP="dialout"

[dsp1760.rules]
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A7012OUX", SYMLINK+="dsp1760", MODE="0666", GROUP="dialout"