import os
import openai

def get_diff():
    """Legge le modifiche dal file diff.txt"""
    with open("diff.txt", "r") as file:
        return file.read()

def review_code(diff):
    """Invia le modifiche a ChatGPT per analisi"""
    openai.api_key = os.getenv("OPENAI_API_KEY")

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Sei un esperto di code review. Fornisci feedback concisi e costruttivi sulle modifiche nel codicei, e controlla la sicurezza."},
            {"role": "user", "content": f"Analizza queste modifiche e suggerisci miglioramenti:\n{diff}"}
        ]
    )
    return response["choices"][0]["message"]["content"]

def main():
    diff = get_diff()
    if diff.strip():
        feedback = review_code(diff)
        print("### ChatGPT Review Feedback ###\n")
        print(feedback)
    else:
        print("Nessuna modifica rilevata.")

if __name__ == "__main__":
    main()

