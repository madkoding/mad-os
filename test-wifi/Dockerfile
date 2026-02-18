FROM archlinux:latest

RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm \
        python \
        python-gobject \
        gtk3 \
        iwd \
        wireless_tools \
        networkmanager \
        iproute2 \
        netctl \
        dialog \
        sudo \
        rfkill \
        which \
        bash && \
    rm -rf /var/cache/pacman/pkg/*

RUN useradd -m -G wheel testuser && \
    echo 'testuser ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/testuser && \
    chmod 440 /etc/sudoers.d/testuser

WORKDIR /home/testuser

# Copy mados-wifi files from build context
COPY --chown=testuser:testuser mados-wifi /usr/local/bin/mados-wifi
COPY --chown=testuser:testuser mados_wifi /usr/local/lib/mados_wifi
COPY --chown=testuser:testuser test_backend.py /home/testuser/test_backend.py

RUN chmod +x /usr/local/bin/mados-wifi /home/testuser/test_backend.py

RUN echo 'export PYTHONPATH="/usr/local/lib${PYTHONPATH:+:$PYTHONPATH}"' >> /home/testuser/.bashrc

USER testuser

CMD ["/bin/bash", "-c", "python3 /home/testuser/test_backend.py"]
