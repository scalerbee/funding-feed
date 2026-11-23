<?php
// Copy this file to fundguy-config.php and fill it in.
// Best place: your cPanel HOME folder (one level ABOVE public_html), so it can never be opened in a browser.
// Never upload the filled-in file to GitHub.
define('BREVO_API_KEY', 'paste-your-brevo-api-key-here');   // Brevo → SMTP & API → API keys (you can reuse the contact form's key)
define('BREVO_LIST_ID', 0);                                // Brevo → Contacts → Lists → "Fund Guy Alerts" → the list ID number
define('UNSUB_SECRET', 'paste-a-long-random-string-here');  // must be EXACTLY the same as the UNSUB_SECRET GitHub secret
