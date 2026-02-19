# Arch Linux Docker Testing Environment
FROM archlinux:base

# Update system and install dependencies
RUN pacman -Syu --noconfirm --needed \
    python \
    python-pip \
    python-gobject \
    python-pytest \
    python-pytest-cov \
    gtk3 \
    bluez \
    bluez-utils \
    sudo \
    git \
    && pacman -Sc --noconfirm

# Create non-root user
RUN useradd -m -g users -s /bin/bash testuser && \
    echo "testuser ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/testuser

USER testuser
WORKDIR /home/testuser

# Copy project files
COPY --chown=testuser:testuser tests/ tests/
COPY --chown=testuser:testuser airootfs/ airootfs/

# Set environment for mock backend
ENV MADOS_BT_CONFIG_MODE=test
ENV PYTHONPATH="/home/testuser/airootfs/usr/local/lib:$PYTHONPATH"

# Create test runner script
RUN echo '#!/bin/bash' > /home/testuser/run-tests.sh && \
    echo 'export MADOS_BT_CONFIG_MODE=test' >> /home/testuser/run-tests.sh && \
    echo 'export PYTHONPATH="/home/testuser/airootfs/usr/local/lib:$PYTHONPATH"' >> /home/testuser/run-tests.sh && \
    echo 'python3 -m unittest tests.test_bluetooth_backend tests.test_bluetooth_frontend tests.test_bluetooth_integration -v' >> /home/testuser/run-tests.sh && \
    chmod +x /home/testuser/run-tests.sh

EXPOSE 22

ENTRYPOINT ["/home/testuser/run-tests.sh"]
