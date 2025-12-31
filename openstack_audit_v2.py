import openstack
import pandas as pd
import datetime
import os

# --- CONFIGURATION ---
# Output filename
OUTPUT_FILE = f"openstack_inventory_{datetime.date.today()}.xlsx"

# Connect to OpenStack (Uses your sourced admin-openrc credentials)
conn = openstack.connect()

def get_project_map():
    """
    Fetches all projects to map IDs to Names.
    Safe read-only operation (Keystone).
    """
    print("Fetching Project list...")
    try:
        projects = list(conn.identity.projects())
        return {p.id: p.name for p in projects}
    except Exception as e:
        print(f"Warning: Could not fetch projects (Check permissions): {e}")
        return {}

def audit_volumes(project_map):
    """
    Fetches Cinder Volumes.
    Safe read-only operation.
    """
    print("Fetching Volumes...")
    try:
        # fetch all volumes across all projects
        vols = list(conn.block_storage.volumes(all_projects=True))
        
        data = []
        for v in vols:
            proj_name = project_map.get(v.project_id, f"Unknown ID ({v.project_id})")
            
            data.append({
                'Project Name': proj_name,
                'Project ID': v.project_id,
                'Volume Name': v.name,
                'Volume ID': v.id,
                'Status': v.status,
                'Size (GB)': v.size,
                'Type': v.volume_type,
                'Created At': v.created_at,
                'Bootable': v.is_bootable
            })
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error fetching volumes: {e}")
        return pd.DataFrame()

def audit_volume_snapshots(project_map):
    """
    Fetches Cinder Volume Snapshots.
    Safe read-only operation.
    """
    print("Fetching Volume Snapshots...")
    try:
        # fetch all snapshots across all projects
        snaps = list(conn.block_storage.snapshots(all_projects=True))
        
        data = []
        for s in snaps:
            proj_name = project_map.get(s.project_id, f"Unknown ID ({s.project_id})")
            
            data.append({
                'Project Name': proj_name,
                'Project ID': s.project_id,
                'Snapshot Name': s.name,
                'Snapshot ID': s.id,
                'Source Volume ID': s.volume_id,
                'Size (GB)': s.size,
                'Status': s.status,
                'Created At': s.created_at
            })
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error fetching volume snapshots: {e}")
        return pd.DataFrame()

def audit_instance_snapshots_and_images(project_map):
    """
    Fetches Glance Images (includes Instance Snapshots).
    Safe read-only operation.
    """
    print("Fetching Images (Instance Snapshots)...")
    try:
        # fetch all images
        images = list(conn.image.images())
        
        data = []
        for img in images:
            # Glance uses 'owner' instead of 'project_id' usually
            proj_id = img.owner
            proj_name = project_map.get(proj_id, f"Unknown ID ({proj_id})")
            
            # Identify if it is likely a snapshot or a base image
            img_type = "Image"
            if img.get('image_type') == 'snapshot':
                img_type = "Instance Snapshot"
            
            data.append({
                'Project Name': proj_name,
                'Project ID': proj_id,
                'Image Name': img.name,
                'Image ID': img.id,
                'Type': img_type,
                'Disk Format': img.disk_format,
                'Container Format': img.container_format,
                # Size in Glance is bytes, converting to GB for readability
                'Size (GB)': (img.size / 1024**3) if img.size else 0,
                'Status': img.status,
                'Visibility': img.visibility
            })
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error fetching images: {e}")
        return pd.DataFrame()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        print("--- Starting OpenStack Inventory Audit ---")
        
        # 1. Get Projects
        p_map = get_project_map()
        
        # 2. Get Data
        df_vols = audit_volumes(p_map)
        df_snaps = audit_volume_snapshots(p_map)
        df_images = audit_instance_snapshots_and_images(p_map)
        
        # 3. Write to Excel
        print(f"Writing to {OUTPUT_FILE}...")
        with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
            if not df_vols.empty:
                df_vols.to_excel(writer, sheet_name='Volumes', index=False)
            if not df_snaps.empty:
                df_snaps.to_excel(writer, sheet_name='Volume Snapshots', index=False)
            if not df_images.empty:
                df_images.to_excel(writer, sheet_name='Instance Snapshots & Images', index=False)
                
        print(f"\nSUCCESS! Audit complete.")
        print(f"File saved: {os.path.abspath(OUTPUT_FILE)}")
        
    except KeyboardInterrupt:
        print("\nAudit cancelled by user.")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
