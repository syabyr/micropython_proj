def connect():
    import network
    
    import ujson
    json_config = open('config.json', "r", encoding="utf-8")
    config = ujson.loads(json_config.read())

    sta_if = network.WLAN(network.STA_IF);
    sta_if.active(True);
    # sta_if.scan()
    sta_if.config(dhcp_hostname=config["device_id"])
    sta_if.connect(config["ssid"], config["password"])
    sta_if.isconnected()
