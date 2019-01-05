# Latest Ubuntu 14.04LTS

FROM ubuntu:trusty

RUN \
    apt-get update && \
    apt-get install --no-install-recommends -y software-properties-common && \
    apt-add-repository ppa:ansible/ansible && \
    apt-get update && \
    apt-get install -y ansible

RUN echo '[local]\nlocalhost\n' > /etc/ansible/hosts

RUN \
    adduser --disabled-password --gecos '' ubuntu && \
    adduser ubuntu sudo && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

COPY playbook.yml /provision/
COPY ansible.cfg /provision/
COPY ansible.gitconfig /provision/
COPY builder.sh /provision/
RUN chown -R ubuntu /provision/

COPY id_rsa /home/ubuntu/.ssh/
COPY solo-builder.pem /home/ubuntu/.ssh/
RUN chown -R ubuntu /home/ubuntu && chmod 0400 /home/ubuntu/.ssh/*

RUN \
    su -l ubuntu -c "\
    export HOME=/home/ubuntu && \
    cd /provision && \
    eval \`ssh-agent\` && \
    ssh-add ~/.ssh/id_rsa && \
    ssh-add ~/.ssh/solo-builder.pem && \
    ansible-playbook -i "localhost," -c local playbook.yml"
