{pkgs}: {
  deps = [
    pkgs.wget
    pkgs.mailutils
    pkgs.iana-etc
    pkgs.postgresql
    pkgs.openssl
  ];
}
