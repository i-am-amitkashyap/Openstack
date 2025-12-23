#!/bin/bash                                                   
      set -e
 
      # STRICT: Only game-02 project
      source ~/.openstack-cli/bin/activate
      export OS_AUTH_URL='http://192.168.2.210:5000'
      export OS_USERNAME='admin'
      export OS_PASSWORD='2cdX2Fsfauu4FembSQyMETQcJR3IhmkxwQAevAAy'
      export OS_PROJECT_NAME='game-02'
      export OS_PROJECT_DOMAIN_NAME='Default'
      export OS_USER_DOMAIN_NAME='Default'
      export OS_REGION_NAME='RegionOne'
 
      echo "=============================================="
      echo "SNAPSHOT CLEANUP - game-02 PROJECT ONLY"
      echo "=============================================="
      echo ""
 
      # Verify we're in game-02
      PROJECT_ID=$(openstack project show game-02 -f value -c id
      2>/dev/null || echo "NOTFOUND")
      echo "Target Project: game-02 ($PROJECT_ID)"
      echo ""
 
      # Snapshot names to clean (duplicates > 1, excluding ncr-* and
       misc)
      NAMES_TO_CLEAN=(
        "lin-ws2-BT-1"
        "web1-BT-1"
        "lin-ws1-BT-1"
        "g1z1l2-G1"
        "g1z1l1-G1"
        "btrtr1-BT-1"
        "app1-BT-1"
        "tentacleVm_1"
        "telegrafVm_2"
        "gng01ten-G1"
        "g1bo1ten-G1"
        "g1b02ten-G1"
        "kali-2-RT"
        "kali-1-RT"
        "blue-1-snapshot-20241017"
        "blue-2-snapshot-20241017"
        "blue-3-snapshot-20241017"
        "blue-4-snapshot-20241017"
        "red-1-snapshot-20241017"
        "red-2-snapshot-20241017"
        "red-3-snapshot-20241017"
        "red-4-snapshot-20241017"
      )
 
      TOTAL_DELETED=0
      TOTAL_KEPT=0
 
      for NAME in "${NAMES_TO_CLEAN[@]}"; do
        echo "--- Processing: $NAME ---"
 
        # Get all snapshots with this name, sorted by created_at
      (newest first)
        # IMPORTANT: Filter by project to ensure we only touch
      game-02
        SNAPSHOTS=$(openstack image list --property
      image_type=snapshot --name "$NAME" --project "$PROJECT_ID" -f
      json 2>/dev/null | jq -r '.[].ID')
 
        if [ -z "$SNAPSHOTS" ]; then
          echo "  No snapshots found, skipping."
          continue
        fi
 
        # Get IDs with creation dates, sort by date (newest first)
        SORTED_IDS=""
        for id in $SNAPSHOTS; do
          created=$(openstack image show "$id" -f value -c
      created_at 2>/dev/null)
          project=$(openstack image show "$id" -f value -c owner
      2>/dev/null)
 
          # Double-check project ownership
          if [ "$project" != "$PROJECT_ID" ]; then
            echo "  SKIPPING $id - belongs to different project!"
            continue
          fi
 
          SORTED_IDS="$SORTED_IDS$created $id\n"
        done
 
        # Sort and get IDs (newest first)
        SORTED=$(echo -e "$SORTED_IDS" | sort -r | awk '{print $2}')
 
        COUNT=0
        KEEP_ID=""
        for id in $SORTED; do
          COUNT=$((COUNT + 1))
          if [ $COUNT -eq 1 ]; then
            KEEP_ID=$id
            echo "  KEEPING: $id (newest)"
            TOTAL_KEPT=$((TOTAL_KEPT + 1))
          else
            echo "  DELETING: $id"
            openstack image delete "$id"
            TOTAL_DELETED=$((TOTAL_DELETED + 1))
          fi
        done
        echo ""
      done
 
      echo "=============================================="
      echo "CLEANUP COMPLETE"
      echo "  Kept: $TOTAL_KEPT snapshots"
      echo "  Deleted: $TOTAL_DELETED snapshots"
      echo "=============================================="
