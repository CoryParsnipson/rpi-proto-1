install:
	sudo mkdir -p /usr/bin/status_overlay
	sudo cp status_overlay.py /usr/bin/status_overlay/status_overlay.py
	sudo cp -r images /usr/bin/status_overlay
	sudo cp -rL lib /usr/bin/status_overlay
	sudo cp status_overlay.service /lib/systemd/system/status_overlay.service
	sudo systemctl daemon-reload
	sudo systemctl enable status_overlay.service
	sudo systemctl start status_overlay.service

reload:
	sudo systemctl daemon-reload

start:
	sudo systemctl start status_overlay.service

stop:
	sudo systemctl stop status_overlay.service

status:
	sudo systemctl status status_overlay.service

enable:
	sudo systemctl enable status_overlay.service

disable:
	sudo systemctl disable status_overlay.service

clean: stop disable
	sudo rm -rf /usr/bin/status_overlay
	sudo rm /lib/systemd/system/status_overlay.service

.PHONY: install disable
