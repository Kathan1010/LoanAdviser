package com.example.ailoanadvisor

import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.google.firebase.auth.FirebaseAuth

class SignupActivity : AppCompatActivity() {

    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_signup)

        auth = FirebaseAuth.getInstance()

        val etName = findViewById<TextInputEditText>(R.id.etSignupName)
        val etEmail = findViewById<TextInputEditText>(R.id.etSignupEmail)
        val etPassword = findViewById<TextInputEditText>(R.id.etSignupPassword)
        val etConfirmPassword = findViewById<TextInputEditText>(R.id.etConfirmPassword)

        val btnSignup = findViewById<MaterialButton>(R.id.btnSignup)
        val tvBackToLogin = findViewById<TextView>(R.id.tvBackToLogin)

        btnSignup.setOnClickListener {

            val name = etName.text.toString().trim()
            val email = etEmail.text.toString().trim()
            val pass = etPassword.text.toString().trim()
            val confirm = etConfirmPassword.text.toString().trim()

            if (name.isEmpty() || email.isEmpty() || pass.isEmpty() || confirm.isEmpty()) {
                Toast.makeText(this, "Please fill all fields", Toast.LENGTH_SHORT).show()

            } else if (pass != confirm) {
                Toast.makeText(this, "Passwords do not match", Toast.LENGTH_SHORT).show()

            } else {
                auth.createUserWithEmailAndPassword(email, pass)
                    .addOnCompleteListener { task ->

                        if (task.isSuccessful) {
                            Toast.makeText(this, "Signup Successful!", Toast.LENGTH_SHORT).show()

                            startActivity(Intent(this, ChatActivity::class.java))
                            finish()

                        } else {
                            Toast.makeText(
                                this,
                                "Signup Failed: ${task.exception?.message}",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    }
            }
        }

        tvBackToLogin.setOnClickListener {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }
}
