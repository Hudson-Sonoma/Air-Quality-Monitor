# Architecture.md

We have a large problem of e-waste. As products are made and discarded, valuable resources are lost and the waste poisons people and the environment.
See [Ghana: A Week in a Toxic Waste Dump](https://www.youtube.com/watch?v=LGBqUM29vic)

* Imagine that electronic components were documented and open source so that they can be used and re-used in many different applications, greatly extending their useful life.
* Imagine that device firmware was open source and available to be modified so hardware can be updated to meet future requirements.
* Imagine that source code was included on-device, and is architected simply, and is written in a popular language, so that little special knowledge is needed.

This project is an example to try to meet these aspirations.

Architecture

1. Components are documented, open source, and commercially available.
2. Device can be assembled and repaired with little to no soldering.
3. Firmware source is stored on-device in a CircuitPython USB FAT volume.
4. Updated firmware is available on github, and can be easily cloned onto the device.
4. Dependent library source is available on github.
5. Circuitpython code is simple to understand, with a setup() function and explicit dispatch loop().
6. Circuitpython async and interrupts are reserved for the system level, simplifying control flow.
7. Circuitpython board modules comprise a hardware abstraction layer that simplifies coding.
8. A laser cut plywood enclosure allow for easy modifications made at your local makerspace.
9. An optional subscription for future managed updates allows for funds for ongoing development.
