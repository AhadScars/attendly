# Attendly

Product site for NFC school attendance and school-bus tracking.

- `index.html` — Attendly Gate. NFC tag on the bag, tap at the school gate, FCM push to parents.
- `ride.html` — Attendly Ride. Same tag on the bus, live GPS map, boarding / approaching-stop / arrival pushes.

```bash
python3 -m http.server 5173
# or: ./run.sh
```

On Windows: `run.bat`

Then open http://localhost:5173
