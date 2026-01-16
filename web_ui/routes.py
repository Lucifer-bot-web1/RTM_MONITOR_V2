import json  # Ensure this is imported at top


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    if current_user.role != 'ADMIN':
        flash("Access Denied", "danger")
        return redirect(url_for('main.dashboard'))

    # --- HANDLE FORM SUBMISSIONS ---
    if request.method == 'POST':
        sec = request.form.get("section")

        if sec == "theme":
            st = request.form.get("theme_style")
            Setting.set("theme_style", st)
            flash("Theme updated.", "success")

        elif sec == "time":
            Setting.set("timezone", request.form.get("timezone", "Asia/Kolkata"))
            Setting.set("time_format", request.form.get("time_format", "DD-MM-YYYY HH:mm:ss"))
            flash("Time settings saved.", "success")

        elif sec == "ping":
            Setting.set("ping_timeout_sec", request.form.get("ping_timeout_sec", "30"))
            Setting.set("up_success_threshold", request.form.get("up_success_threshold", "15"))
            flash("Ping engine updated.", "success")

        elif sec == "alarm":
            Setting.set("alarm_duration_sec", request.form.get("alarm_duration_sec", "10"))
            flash("Alarm settings saved.", "success")

        elif sec == "telegram":
            Setting.set("telegram_token", request.form.get("telegram_token", "").strip())
            Setting.set("telegram_chat_id", request.form.get("telegram_chat_id", "").strip())
            flash("Telegram config saved.", "success")

        elif sec == "templates":
            data = {
                "down": request.form.get("down", ""),
                "up": request.form.get("up", ""),
                "add": request.form.get("add", ""),
                "pause": request.form.get("pause", ""),
                "stop": request.form.get("stop", ""),
                "delete": request.form.get("delete", ""),
            }
            Setting.set("message_templates", json.dumps(data))
            flash("Templates updated.", "success")

        return redirect(url_for('main.settings_page'))

    # --- LOAD DATA FOR TEMPLATE ---
    # Load Templates safely
    try:
        tpls = json.loads(Setting.get("message_templates", "{}"))
    except:
        tpls = {}

    return render_template('settings.html',
                           themes=["dark_glass", "light_glass", "neon_blue", "cyber_3d"],
                           current_theme=Setting.get("theme_style", "dark_glass"),
                           tzname=Setting.get("timezone", "Asia/Kolkata"),
                           fmt=Setting.get("time_format", "DD-MM-YYYY HH:mm:ss"),
                           ping_timeout_sec=Setting.get("ping_timeout_sec", "30"),
                           up_threshold=Setting.get("up_success_threshold", "15"),
                           alarm_sec=Setting.get("alarm_duration_sec", "10"),
                           token=Setting.get("telegram_token", ""),
                           chat_id=Setting.get("telegram_chat_id", ""),
                           templates=tpls
                           )