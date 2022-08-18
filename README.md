# Mailbox Notifier

This project is designed to provide you with a visual notification when your mailbox has been opened, to notify you that you have mail.

## Parts list:
* [Adafruit ESP32-S2 Feather](https://www.adafruit.com/product/5000)
* [Adafruit LoRa Radio FeatherWing - RFM95W 900MHz](https://www.adafruit.com/product/3231)
* [Female Header Kit for Feather](https://www.adafruit.com/product/2886)
* [Adafruit BQ24074 Universal USB/DC/Solar LiPoly/LiIon charger](https://www.adafruit.com/product/4755)
* [Solar Panel (this link is an example, any panel from Adafruit should work)](https://www.adafruit.com/product/5366)
* [3.5mm/1.1mm to 5.5mm/2.1mm DC Jack Adapter](https://www.adafruit.com/product/4287)
* [Lithium Ion Battery Pack - 3.7V, 4400mAh](https://www.adafruit.com/product/354)
* [JST-PH 2-pin Jumper Cable - 100mm long](https://www.adafruit.com/product/4714)
* [1N5818 Schottky diode](https://www.digikey.com/en/products/detail/onsemi/1N5818G/1474209?s=N4IgjCBcoLQBxVAYygMwIYBsDOBTANCAPZQDaIALHAgLoC%2BdhATGeAHICscYcA4iPSA)
* [Small Plastic Project Enclosure](https://www.adafruit.com/product/903)
* Any Raspberry Pi, though the LoRa Bonnet is the same size as the PiZeroW/PiZero2W.
* [Adafruit LoRa Bonnet with OLED - RFM952 @ 915MHz](https://www.adafruit.com/product/4074)
* "Normally open" reed switch. **"Normally open" is a requirement!** The code will not work with a "normally closed" switch. Available on Amazon, etc.
### Antenna options:
##### Option one:
* [Hookup wire (link is to many options)](https://www.adafruit.com/?q=solid-core+wire+spool&p=1&sort=BestMatch)
##### Option two, if option one isn't providing enough signal strength:
* [900MHz Antenna Kit](https://www.adafruit.com/product/3340)
* [uFL SMT Antenna Connector](https://www.adafruit.com/product/1661)

## Tools and extras required:
* Power drill
* Step drill bit set (not required, but makes the build much easier)
* Standard drill bit set
* 29/64in drill bit (this is a very odd size, but perfect for the solar panel adapter. It will not be included in a standard kit. You can always go with a larger bit, and add more sealant in the final build.)
* [3M Command Adhesive Medium Picture Hanging Strips](https://www.command.com/3M/en_US/command/products/~/Command-Medium-Picture-Hanging-Strips/?N=5924736+3294529207+3294774739&rt=rud)
* RTV silicone sealant (J-B Weld is a good option. Available on Amazon, etc.)