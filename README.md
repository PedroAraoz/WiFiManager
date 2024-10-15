# WiFiManager
Used to give WiFi access to pico W projects without the need to hardcode credentials. Especially useful for projects that are going to be moving around or for when you don't know the WiFi at build time.

## How it works
Tries to load credentials from the `credentials` file. If they are not present or if they are incorrect, it will create an access point in which you can connect and through a webpage, load the credentials to be saved.
