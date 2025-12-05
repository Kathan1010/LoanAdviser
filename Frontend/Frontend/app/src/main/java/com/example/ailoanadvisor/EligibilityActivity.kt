package com.example.ailoanadvisor

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.ailoanadvisor.databinding.ActivityEligibilityBinding

class EligibilityActivity : AppCompatActivity() {

    // Use ViewBinding for safer and cleaner view access
    private lateinit var binding: ActivityEligibilityBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityEligibilityBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // The Spinner is populated from the XML layout (`android:entries`),
        // so we don't need to set an adapter here.

        binding.btnCheck.setOnClickListener {
            // Get text from input fields
            val ageStr = binding.etAge.text.toString()
            val incomeStr = binding.etIncome.text.toString()
            val emiStr = binding.etEmi.text.toString()

            // Validate that inputs are not empty
            if (ageStr.isEmpty() || incomeStr.isEmpty() || emiStr.isEmpty()) {
                Toast.makeText(this, "Please fill in all fields", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Safely parse numbers
            val age = ageStr.toInt()
            val income = incomeStr.toDouble()
            val emi = emiStr.toDouble()

            // --- Eligibility Logic ---
            if (age < 21 || age > 60) {
                binding.tvResult.text = "❌ Not Eligible: Age must be between 21–60"
                return@setOnClickListener
            }

            if (income < 25000) {
                binding.tvResult.text = "❌ Not Eligible: Minimum income should be ₹25,000"
                return@setOnClickListener
            }

            if (emi > income * 0.4) {
                binding.tvResult.text = "❌ Not Eligible: Existing EMI cannot exceed 40% of income"
                return@setOnClickListener
            }

            // If all checks pass
            binding.tvResult.text = "✅ ELIGIBLE FOR LOAN\n\nYou can apply safely!"
        }
    }
}
