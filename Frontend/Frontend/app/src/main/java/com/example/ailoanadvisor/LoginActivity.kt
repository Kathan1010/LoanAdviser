package com.example.ailoanadvisor

import android.content.Intent
import android.os.Bundle
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.firebase.auth.FirebaseAuth

class LoginActivity : AppCompatActivity() {

    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        auth = FirebaseAuth.getInstance()

        // ✅ Auto Login if user already logged in
        if (auth.currentUser != null) {
            startActivity(Intent(this, ChatActivity::class.java))
            finish()
        }

        val etEmail = findViewById<EditText>(R.id.etEmail)
        val etPassword = findViewById<EditText>(R.id.etPassword)
        val btnLogin = findViewById<MaterialButton>(R.id.btnLogin)
        val tvSignup = findViewById<TextView>(R.id.tvSignup)
        val btnGoogle = findViewById<MaterialButton>(R.id.btnGoogleLogin)

        // ✅ Email + Password Login
        btnLogin.setOnClickListener {

            val email = etEmail.text.toString().trim()
            val pass = etPassword.text.toString().trim()

            if (email.isEmpty() || pass.isEmpty()) {
                Toast.makeText(this, "Enter email & password", Toast.LENGTH_SHORT).show()
            } else {

                auth.signInWithEmailAndPassword(email, pass)
                    .addOnCompleteListener { task ->

                        if (task.isSuccessful) {
                            Toast.makeText(this, "Login Successful!", Toast.LENGTH_SHORT).show()
                            startActivity(Intent(this, ChatActivity::class.java))
                            finish()
                        } else {
                            Toast.makeText(
                                this,
                                "Login Failed: ${task.exception?.message}",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    }
            }
        }

        // ✅ Redirect to Signup Screen
        tvSignup.setOnClickListener {
            startActivity(Intent(this, SignupActivity::class.java))
        }

        // ✅ Google Login Button (already working)
        btnGoogle.setOnClickListener {
            // Keep your existing Google login code here
        }
    }
}
