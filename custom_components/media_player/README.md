A component will be loaded on start if a section (ie. `media_player:`) for it exists in the config file. Home Assistant will use the directory that contains your config file as the directory that holds your customizations. Custom components can be loaded from `<config directory>/custom_components/<component name>`.

```yaml
media_player:
  - platform: enigma2
    host: hostname/ip
```
