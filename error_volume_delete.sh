for VOL in $(openstack volume list --all-projects \
  --status error_deleting -f value -c ID); do
  echo "Processing volume: $VOL"

  # Reset state
  openstack volume set --state available $VOL

  # Delete volume
  openstack volume delete $VOL
done
