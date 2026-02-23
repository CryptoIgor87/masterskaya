from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from web.app import templates
from config import BASE_PATH
import database as db

router = APIRouter(prefix="/admin/feedback", tags=["feedback"])


@router.get("")
async def list_feedback(request: Request, filter: str = "all"):
    messages = await db.get_all_feedback()
    if filter == "replied":
        messages = [m for m in messages if m["is_replied"]]
    elif filter == "unreplied":
        messages = [m for m in messages if not m["is_replied"]]
    return templates.TemplateResponse("feedback.html", {
        "request": request,
        "messages": messages,
        "active_page": "feedback",
        "current_filter": filter,
    })


@router.post("/{feedback_id}/reply")
async def reply_to_feedback(
    feedback_id: int,
    request: Request,
    reply_text: str = Form(...),
):
    await db.set_feedback_reply(feedback_id, reply_text)

    feedback = await db.get_feedback(feedback_id)
    if feedback:
        client = await db.get_client(feedback["client_id"])
        if client:
            bot = request.app.state.bot
            if bot:
                try:
                    await bot.send_message(
                        chat_id=client["telegram_id"],
                        text=f"\U0001f4ac <b>Ответ от магазина:</b>\n\n{reply_text}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    return RedirectResponse(f"{BASE_PATH}/admin/feedback", status_code=303)


@router.post("/{feedback_id}/delete")
async def delete_feedback(feedback_id: int):
    await db.delete_feedback(feedback_id)
    return RedirectResponse(f"{BASE_PATH}/admin/feedback", status_code=303)
