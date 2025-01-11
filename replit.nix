{pkgs}: {
  deps = [
    pkgs.mailutils
    pkgs.iana-etc
    pkgs.postgresql
    pkgs.openssl
  ];
}
